#!/usr/bin/env python3
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0

"""Run standalone releasetools with Aura A1's boot image header policy."""

import argparse
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-tools", required=True, type=Path,
                        help="host tools root containing bin/ (build output or otatools)")
    parser.add_argument("tool", choices=("add_img_to_target_files",
                                        "sign_target_files_apks",
                                        "ota_from_target_files"))
    parser.add_argument("args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    host_bin = args.host_tools.resolve() / "bin"
    tool = host_bin / args.tool
    stock = host_bin / "mkbootimg"
    wrapper = Path(__file__).resolve().with_name("aura_a1_mkbootimg.py")
    for executable in (tool, stock, wrapper):
        if not executable.is_file() or not os.access(executable, os.X_OK):
            parser.error(f"executable missing: {executable}")
    env = os.environ.copy()
    env["MKBOOTIMG"] = str(wrapper)
    env["AURA_A1_STOCK_MKBOOTIMG"] = str(stock)
    env["PATH"] = str(host_bin) + os.pathsep + env.get("PATH", "")
    os.execve(str(tool), [str(tool), *args.args], env)


if __name__ == "__main__":
    main()
