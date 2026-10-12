#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
"""Prepare a stock package/unpacked dump for the standard extract-files.py."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path, help='SPFlashTool IMAGES directory or complete unpack-stock.py output')
    p.add_argument('--out', required=True, type=Path, help='New staging directory')
    p.add_argument('--lineage', type=Path, default=Path.home() / 'android/lineage')
    a = p.parse_args()
    source, out = a.source.resolve(), a.out.resolve()
    if out.exists():
        p.error('Staging output exists; choose a new directory')
    out.mkdir(parents=True)
    if (source / 'super.img').is_file():
        unpacked = out / 'unpacked'
        subprocess.run([sys.executable, str(Path(__file__).parent / 'extract/stock.py'),
                        '--stock', str(source), '--out', str(unpacked), '--lineage', str(a.lineage)], check=True)
        source = unpacked
    status = json.loads((source / 'extraction-status.json').read_text())
    if not status['complete']:
        p.error('Incomplete extraction / OTA COW snapshots are not a supported blob source')
    inputs = {
        'vendor.img': 'images/vendor_a.img',
        'vendor_dlkm.img': 'images/vendor_dlkm_a.img',
        'system_dlkm.img': 'images/system_dlkm_a.img',
        'odm_dlkm.img': 'images/odm_dlkm_a.img',
        'kernel/Image.lz4': 'boot/kernel',
        'kernel/dtb.img': 'vendor_boot/dtb',
        'kernel/dtbo.img': 'dtbo.img',
        'ramdisk/platform.lz4': 'vendor_boot/vendor_ramdisk00',
    }
    manifest = {}
    for destination, relative in inputs.items():
        src = source / relative
        if not src.is_file():
            p.error(f'Missing source file: {src}')
        dst = out / 'prebuilt' / destination
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.symlink_to(src)
        with src.open('rb') as f:
            manifest[f'prebuilt/{destination}'] = hashlib.file_digest(f, 'sha256').hexdigest()
    modules = source / 'vendor_boot/vendor_ramdisk00-root/lib/modules'
    if len(list(modules.glob('*.ko'))) != 174:
        p.error('Unexpected vendor ramdisk module set; update the matched release and file list first')
    (out / 'prebuilt/ramdisk/modules').symlink_to(modules, target_is_directory=True)
    # Keep original partitions available for later file-level extraction.
    for name in ('vendor', 'system', 'system_ext', 'product', 'system_dlkm', 'vendor_dlkm', 'odm_dlkm'):
        (out / name).symlink_to(source / name, target_is_directory=True)
    (out / 'source-SHA256.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Prepared source: {out}')


if __name__ == '__main__':
    main()
