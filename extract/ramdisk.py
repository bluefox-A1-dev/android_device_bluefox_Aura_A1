# SPDX-FileCopyrightText: 2026 The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
"""Deterministic first-stage archive; never carry OEM init/recovery/policy into Lineage."""
from pathlib import Path
import stat
import subprocess


def pack_first_stage(root: Path, output: Path):
    files = list((root / 'lib/modules').iterdir())
    files += [root / 'first_stage_ramdisk/fstab.mt6789']
    entries = {Path('.'), Path('lib'), Path('lib/modules'), Path('first_stage_ramdisk')}
    entries.update(p.relative_to(root) for p in files)
    archive = bytearray()

    def append(name, mode, content, inode):
        encoded = name.encode() + b'\0'
        fields = [inode, mode, 0, 0, 1, 0, len(content), 0, 0, 0, 0, len(encoded), 0]
        archive.extend(b'070701' + ''.join(f'{n:08x}' for n in fields).encode())
        archive.extend(encoded)
        archive.extend(b'\0' * (-len(archive) % 4))
        archive.extend(content)
        archive.extend(b'\0' * (-len(archive) % 4))

    for inode, entry in enumerate(sorted(entries), 1):
        source = root / entry
        if source.is_symlink():
            raise ValueError(f'Unexpected symlink in first-stage input: {source}')
        if source.is_dir():
            append(str(entry), stat.S_IFDIR | 0o755, b'', inode)
        elif source.is_file():
            append(str(entry), stat.S_IFREG | stat.S_IMODE(source.stat().st_mode), source.read_bytes(), inode)
        else:
            raise ValueError(f'Unexpected first-stage input: {source}')
    append('TRAILER!!!', 0, b'', len(entries) + 1)
    archive.extend(b'\0' * (-len(archive) % 512))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('wb') as f:
        subprocess.run(['lz4', '-l', '-12', '--favor-decSpeed', '-c'], input=bytes(archive), stdout=f, check=True)
