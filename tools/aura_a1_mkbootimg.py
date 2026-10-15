#!/usr/bin/env python3
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0

"""Keep Aura A1 GKI v4 header versions zero, before image signing."""

import argparse
import os
from pathlib import Path
import sys


def main():
    # Parse only the options needed to identify a boot-format v4 output. Leave
    # vendor_boot-only and older header formats unchanged. argparse follows
    # mkbootimg's last-option-wins semantics, including --option=value syntax.
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--header_version", type=int, default=0)
    parser.add_argument("--output", "-o")
    args, _ = parser.parse_known_args()
    command = sys.argv[1:]
    if args.header_version == 4 and args.output:
        command += ["--os_version", "0", "--os_patch_level", "0"]

    # Installed beside the stock tool; the standalone release entry point
    # supplies an explicit path when executing this script from the device tree.
    stock = Path(os.environ.get(
        "AURA_A1_STOCK_MKBOOTIMG", Path(__file__).resolve().with_name("mkbootimg")))
    if stock.resolve() == Path(__file__).resolve():
        sys.exit("aura_a1_mkbootimg: stock tool must not be this wrapper")
    if not stock.is_file() or not os.access(stock, os.X_OK):
        sys.exit(f"aura_a1_mkbootimg: stock executable missing: {stock}")
    os.execv(str(stock), [str(stock), *command])


if __name__ == "__main__":
    main()
