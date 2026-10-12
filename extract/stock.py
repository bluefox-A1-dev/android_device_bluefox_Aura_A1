#!/usr/bin/env python3
"""Read-only stock dump extraction. No mounts, flashing, or calibration data export."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import struct
import subprocess
import sys


def checked_checksum(data, start, expected):
    copy = bytearray(data)
    copy[start:start + 32] = b'\0' * 32
    if hashlib.sha256(copy).digest() != expected:
        raise ValueError('LP metadata checksum mismatch')


def read_super(image, out, metadata_slot, slot):
    with image.open('rb') as f:
        f.seek(4096)
        geometry = f.read(52)
        magic, size, checksum, max_size, slots, block_size = struct.unpack('<II32sIII', geometry)
        if magic != 0x616c4467 or size != 52:
            raise ValueError('Expected raw Android super image with LP geometry')
        checked_checksum(geometry, 8, checksum)
        if metadata_slot >= slots:
            raise ValueError('Metadata slot is outside LP geometry')
        f.seek(12288 + max_size * metadata_slot)
        prefix = f.read(12)
        magic, major, minor, header_size = struct.unpack('<IHHI', prefix)
        if magic != 0x414c5030 or major != 10 or minor > 2 or header_size not in (128, 256):
            raise ValueError('Unsupported LP header')
        f.seek(12288 + max_size * metadata_slot)
        header = f.read(header_size)
        checked_checksum(header, 12, header[12:44])
        tables_size = struct.unpack_from('<I', header, 44)[0]
        if tables_size + header_size > max_size:
            raise ValueError('LP tables exceed metadata area')
        tables = f.read(tables_size)
        if hashlib.sha256(tables).digest() != header[48:80]:
            raise ValueError('LP table checksum mismatch')

        def table(offset, fmt):
            start, count, entry_size = struct.unpack_from('<III', header, offset)
            if entry_size != struct.calcsize(fmt) or start + count * entry_size > len(tables):
                raise ValueError('Invalid LP table bounds')
            return [struct.unpack_from(fmt, tables, start + n * entry_size) for n in range(count)]

        partitions = table(80, '<36sIIII')
        extents = table(92, '<QIQI')
        groups = table(104, '<36sIQ')
        devices = table(116, '<QIIQ36sI')
        result = dict(metadata_slot=metadata_slot, slot=slot, metadata_max_size=max_size, metadata_slots=slots, logical_block_size=block_size,
                      flags=struct.unpack_from('<I', header, 128)[0] if header_size == 256 else 0,
                      groups=[dict(name=n.rstrip(b'\0').decode(), flags=fl, maximum_size=s) for n, fl, s in groups],
                      block_devices=[dict(first_sector=x[0], alignment=x[1], size=x[3], name=x[4].rstrip(b'\0').decode()) for x in devices],
                      partitions=[])
        for raw_name, attributes, first, count, group in partitions:
            name = raw_name.rstrip(b'\0').decode()
            if '/' in name or name in ('.', '..') or first + count > len(extents):
                raise ValueError('Invalid partition entry')
            selected = extents[first:first + count]
            total = sum(x[0] * 512 for x in selected)
            result['partitions'].append(dict(name=name, size=total, attributes=attributes, group=group,
                                            extents=[dict(sectors=x[0], type=x[1], sector=x[2], source=x[3]) for x in selected]))
            if not total or not name.endswith('_' + slot):
                continue
            target = out / (name + '.img')
            print(f'Extract {name}: {total} bytes', flush=True)
            with target.open('xb') as w:
                for sectors, kind, sector, source in selected:
                    remaining = sectors * 512
                    if kind == 1:  # LP_TARGET_TYPE_ZERO
                        w.seek(remaining, 1)
                        continue
                    if kind != 0 or source != 0 or (sector + sectors) * 512 > image.stat().st_size:
                        raise ValueError('Unsupported or out-of-bounds LP extent')
                    f.seek(sector * 512)
                    while remaining:
                        chunk = f.read(min(remaining, 8 * 1024 * 1024))
                        if not chunk:
                            raise ValueError('Truncated extent')
                        w.write(chunk)
                        remaining -= len(chunk)
                w.truncate(total)
        return result


def unpack_cpio(payload, root):
    """Extract newc archives without devices/ownership or following archive symlinks."""
    pos = 0
    hardlinks = {}
    while pos + 110 <= len(payload):
        if payload[pos:pos + 6] not in (b'070701', b'070702'):
            if not any(payload[pos:]):
                break
            raise ValueError('Expected newc cpio ramdisk')
        fields = [int(payload[pos + 6 + i * 8:pos + 14 + i * 8], 16) for i in range(13)]
        ino, mode, uid, gid, nlink, mtime, length, devmaj, devmin, _, _, namesize, _ = fields
        pos += 110
        name = payload[pos:pos + namesize - 1].decode()
        pos = (pos + namesize + 3) & ~3
        data = payload[pos:pos + length]
        if len(data) != length:
            raise ValueError('Truncated cpio entry')
        pos = (pos + length + 3) & ~3
        if name == 'TRAILER!!!':
            continue
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError(f'Unsafe archive path {name}')
        target = root.joinpath(*relative.parts)
        if any(p.is_symlink() for p in target.parents if p != root.parent):
            raise ValueError(f'Archive parent is a symlink: {name}')
        target.parent.mkdir(parents=True, exist_ok=True)
        if stat.S_ISDIR(mode):
            target.mkdir(exist_ok=True)
        elif stat.S_ISLNK(mode):
            target.symlink_to(data.decode())
        elif stat.S_ISREG(mode):
            if target.is_symlink():
                raise ValueError(f'Regular file replaces symlink: {name}')
            target.write_bytes(data)
            if nlink > 1:
                hardlinks.setdefault((devmaj, devmin, ino), []).append(target)
        else:
            continue  # device nodes are not needed for analysis
        if not target.is_symlink():
            target.chmod(stat.S_IMODE(mode))
    for entries in hardlinks.values():
        source = next((p for p in entries if p.stat().st_size), entries[0])
        for p in entries:
            if p != source:
                p.write_bytes(source.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stock', type=Path, default=Path('IMAGES'))
    parser.add_argument('--out', type=Path, default=Path('extracted/firmware'))
    parser.add_argument('--metadata-slot', type=int, choices=range(3), default=0)
    parser.add_argument('--slot', choices=('a', 'b'), default='a')
    parser.add_argument('--lineage', type=Path, default=Path.home() / 'android/lineage')
    args = parser.parse_args()
    source, out = args.stock.resolve(), args.out.resolve()
    if out.exists():
        parser.error('Output already exists; choose a new directory (source is never modified)')
    unpack = args.lineage / 'system/tools/mkbootimg/unpack_bootimg.py'
    for cmd in ('debugfs', 'lz4', 'fsck.erofs'):
        if not shutil.which(cmd):
            parser.error(f'Missing {cmd}')
    if not unpack.is_file():
        parser.error('Missing Lineage unpack_bootimg.py')
    images = out / 'images'
    images.mkdir(parents=True)
    super_image = source / 'super.img'
    with super_image.open('rb') as f:
        sparse = f.read(4) == b'\x3a\xff\x26\xed'
    if sparse:
        simg2img = args.lineage / 'prebuilts/kernel-build-tools/linux-x86/bin/simg2img'
        raw = out / 'super.raw.img'
        subprocess.run([str(simg2img), str(super_image), str(raw)], check=True)
        super_image = raw
    report = read_super(super_image, images, args.metadata_slot, args.slot)
    if not any(images.glob('*.img')):
        raise ValueError('No populated partitions for selected metadata/slot')
    failures = []
    if any(p['name'].endswith('-cow') for p in report['partitions']):
        failures.append('COW snapshots present: raw logical partitions may not match mounted filesystems')
    (out / 'super-metadata.json').write_text(json.dumps(report, indent=2) + '\n')
    for image in sorted(images.glob('*.img')):
        name = image.stem.removesuffix('_a').removesuffix('_b')
        destination = out / name
        if destination.exists():
            raise ValueError('Both slots contain data; extract slots into separate directories')
        destination.mkdir()
        with image.open('rb') as f:
            f.seek(1024)
            erofs = f.read(4) == b'\xe2\xe1\xf5\xe0'
            f.seek(1080)
            ext4 = f.read(2) == b'\x53\xef'
        with (out / f'{image.stem}-extract.log').open('w') as log:
            if erofs:
                rc = subprocess.run(['fsck.erofs', '--no-preserve-owner', f'--extract={destination}', str(image)], stdout=log, stderr=log).returncode
                if rc:
                    failures.append(f'{image.stem}: fsck.erofs returned {rc}; extraction is incomplete')
            elif ext4:
                # debugfs is read-only unless -w is explicitly supplied.
                subprocess.run(['debugfs', '-R', f'rdump / "{destination}"', str(image)], stdout=log, stderr=log, check=True)
            else:
                raise ValueError(f'Unsupported filesystem: {image}')
        if not any(destination.iterdir()):
            raise ValueError(f'Filesystem extraction produced no files: {image}')
    for partition in ('boot', 'init_boot', 'vendor_boot'):
        directory = out / partition
        directory.mkdir()
        with (directory / 'header.txt').open('w') as log:
            boot_image = source / f'{partition}.img'
            if not boot_image.is_file():
                boot_image = source / f'{partition}_{args.slot}.img'
            subprocess.run([sys.executable, str(unpack), '--boot_img', str(boot_image), '--out', str(directory)], stdout=log, check=True)
        for archive in sorted(directory.iterdir()):
            if archive.name == 'ramdisk' or archive.name.startswith('vendor_ramdisk'):
                dest = directory / (archive.name + '-root')
                dest.mkdir()
                payload = subprocess.check_output(['lz4', '-dc', str(archive)])
                unpack_cpio(payload, dest)
    # DTBO total_size excludes padding and AVB; preserve stock partition separately.
    dtbo_image = source / 'dtbo.img'
    if not dtbo_image.is_file():
        dtbo_image = source / f'dtbo_{args.slot}.img'
    dtbo = dtbo_image.read_bytes()
    magic, total = struct.unpack_from('>II', dtbo)
    if magic != 0xd7b7ab1e or total > len(dtbo):
        raise ValueError('Invalid DTBO image')
    (out / 'dtbo.img').write_bytes(dtbo[:total])
    (out / 'extraction-status.json').write_text(json.dumps(dict(complete=not failures, issues=failures), indent=2) + '\n')
    print(f'Extraction finished: {out}; complete={not failures}', flush=True)
    for issue in failures:
        print(f'WARNING: {issue}', flush=True)
    if failures:
        sys.exit(2)


if __name__ == '__main__':
    main()
