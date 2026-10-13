#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
"""Build an explicit diagnostic init_boot; leave the input image untouched."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import struct
import subprocess
import tempfile


def pad4(data):
    return data + bytes((-len(data)) % 4)


def record(header, name, data):
    name = name.encode() + b'\0'
    header = bytearray(header)
    header[54:62] = f'{len(data):08x}'.encode()
    header[94:102] = f'{len(name):08x}'.encode()
    if header[:6] == b'070702':
        header[102:110] = f'{sum(data) & 0xffffffff:08x}'.encode()
    return pad4(bytes(header) + name) + pad4(data)


def wrap_cpio(cpio, wrapper):
    pos = 0
    output = bytearray()
    original_init = None
    names = set()
    while pos + 110 <= len(cpio):
        header = cpio[pos:pos + 110]
        if header[:6] not in (b'070701', b'070702'):
            raise ValueError('Unexpected cpio header')
        size = int(header[54:62], 16)
        name_size = int(header[94:102], 16)
        start = pos + 110
        name = cpio[start:start + name_size - 1].decode()
        data_start = (start + name_size + 3) & ~3
        end = (data_start + size + 3) & ~3
        if end > len(cpio):
            raise ValueError('Truncated cpio record')
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Unsafe archive name')
        normalized = str(path)
        if normalized == 'TRAILER!!!':
            if original_init is None:
                raise ValueError('No init executable in input ramdisk')
            # New init entry; retain the original init's ownership and mode.
            fresh = bytearray(original_init[0])
            fresh[:6] = b'070701'
            fresh[6:14] = b'00a1b001'
            fresh[38:46] = b'00000001'
            fresh[102:110] = b'00000000'
            output += record(fresh, 'init', wrapper)
            output += cpio[pos:]
            return bytes(output), original_init[1]
        if normalized in names or normalized == 'init.aura.real':
            raise ValueError('Duplicate or already wrapped archive')
        names.add(normalized)
        if normalized == 'init':
            mode = int(header[14:22], 16)
            data = cpio[data_start:data_start + size]
            if mode & 0o170000 != 0o100000 or not data.startswith(b'\x7fELF'):
                raise ValueError('init must be a regular ELF executable')
            original_init = (header, data)
            output += record(header, 'init.aura.real', data)
        else:
            output += cpio[pos:end]
        pos = end
    raise ValueError('Missing cpio trailer')


def main():
    device = Path(__file__).resolve().parents[1]
    lineage = device.parents[2]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--cc', type=Path, default=Path.home()/'arm-linux-musleabi-cross/bin/arm-linux-musleabi-gcc')
    a = p.parse_args()
    if a.output.exists() or a.output.with_suffix('.json').exists():
        p.error('Choose a new output; existing files are never overwritten')
    data = a.input.read_bytes()
    if data[:8] != b'ANDROID!' or struct.unpack_from('<I', data, 40)[0] != 4:
        p.error('Only header-v4 init_boot images are supported')
    kernel_size, ramdisk_size = struct.unpack_from('<II', data, 8)
    if kernel_size or struct.unpack_from('<I', data, 1580)[0]:
        p.error('Expected generic init_boot without kernel or embedded boot signature')
    if not ramdisk_size or 4096 + ramdisk_size > len(data):
        p.error('Invalid ramdisk bounds')
    ramdisk = data[4096:4096 + ramdisk_size]
    with tempfile.TemporaryDirectory(prefix='aura-debug-init-') as d:
        root = Path(d)
        exe = root/'init-wrapper'
        subprocess.run([str(a.cc), '-static', '-Os', '-Wall', '-Wextra', '-Werror',
                        '-DAURA_INIT_WRAPPER', str(device/'debug/bootlog.c'), '-o', str(exe)], check=True)
        wrapper = exe.read_bytes()
        if wrapper[:5] != b'\x7fELF\x01' or struct.unpack_from('<H', wrapper, 18)[0] != 40:
            raise ValueError('Expected static ARM32 wrapper; matched stock GKI has CONFIG_COMPAT=y')
        info = subprocess.check_output(['readelf', '-l', str(exe)], text=True)
        if 'INTERP' in info:
            raise ValueError('Wrapper must not require a dynamic loader')
        compressed = root/'ramdisk';compressed.write_bytes(ramdisk)
        if ramdisk[:2] == b'\x1f\x8b':
            cpio = subprocess.check_output(['gzip', '-dc', str(compressed)])
        else:
            cpio = subprocess.check_output(['lz4', '-dc', str(compressed)])
        rebuilt, original = wrap_cpio(cpio, wrapper)
        archive = root/'ramdisk.cpio';archive.write_bytes(rebuilt)
        packed = root/'ramdisk.lz4'
        subprocess.run(['lz4', '-l', '-9', '-f', str(archive), str(packed)], check=True)
        payload = packed.read_bytes()
        header = bytearray(data[:4096])
        struct.pack_into('<I', header, 12, len(payload))
        unsigned = bytes(header) + payload + bytes((-len(payload)) % 4096)
        if len(unsigned) >= 8388608 - 65536:
            raise ValueError('Diagnostic init_boot would exceed the 8 MiB partition')
        candidate = root/'init_boot.img';candidate.write_bytes(unsigned)
        avb = lineage/'external/avb/avbtool.py'
        subprocess.run(['python3', str(avb), 'add_hash_footer', '--image', str(candidate),
                        '--partition_name', 'init_boot', '--partition_size', '8388608',
                        '--algorithm', 'NONE'], check=True)
        # Verify the original init is still embedded unchanged, and header fields
        # other than ramdisk size have not changed.
        expected_header = bytearray(header);expected_header[12:16] = data[12:16]
        assert bytes(expected_header) == data[:4096]
        spec = importlib.util.spec_from_file_location('stock_cpio', device/'extract/stock.py')
        unpack = importlib.util.module_from_spec(spec);spec.loader.exec_module(unpack)
        extracted = root/'verify';extracted.mkdir()
        unpack.unpack_cpio(rebuilt, extracted)
        assert (extracted/'init.aura.real').read_bytes() == original
        assert (extracted/'init').read_bytes() == wrapper
        a.output.parent.mkdir(parents=True, exist_ok=True)
        with a.output.open('xb') as f:f.write(candidate.read_bytes())
        report = {'input': str(a.input.resolve()), 'output': str(a.output.resolve()),
                  'input_sha256': hashlib.sha256(data).hexdigest(),
                  'output_sha256': hashlib.sha256(a.output.read_bytes()).hexdigest(),
                  'original_init_sha256': hashlib.sha256(original).hexdigest(),
                  'kernel_and_dtb_modified': False, 'stock_init_preserved': True,
                  'wrapper': 'static ARM32; GKI CONFIG_COMPAT=y',
                  'log_path': '/metadata/aura-bootlogs', 'hardware_validated': False}
        a.output.with_suffix('.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report, indent=2))


if __name__ == '__main__':main()
