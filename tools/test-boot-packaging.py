#!/usr/bin/env python3
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0

"""Exercise real mkbootimg, releasetools and AVB using temporary test images."""

import argparse
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lineage", required=True, type=Path)
    args = parser.parse_args()
    root = args.lineage.resolve()
    host = root / "out/host/linux-x86/bin"
    tools = Path(__file__).resolve().parent
    sys.path.insert(0, str(root / "build/make/tools/releasetools"))
    import common

    os.environ["PATH"] = str(host) + os.pathsep + os.environ["PATH"]
    os.environ["AURA_A1_STOCK_MKBOOTIMG"] = str(host / "mkbootimg")
    common.OPTIONS.search_path = str(host.parent)
    wrapper = tools / "aura_a1_mkbootimg.py"

    def run(*command):
        return subprocess.check_output([str(x) for x in command], stderr=subprocess.STDOUT)

    def header(data):
        assert data[:8] == b"ANDROID!"
        return struct.unpack_from("<I", data, 40)[0], struct.unpack_from("<I", data, 16)[0]

    with tempfile.TemporaryDirectory(prefix="aura-boot-test-") as temporary:
        temp = Path(temporary)
        for partition in ("boot", "init_boot", "recovery"):
            source = temp / partition.upper()
            source.mkdir()
            (source / "kernel").write_bytes(b"test kernel\n")
            (source / "RAMDISK").mkdir()
            (source / "RAMDISK/init").write_bytes(b"test ramdisk\n")
            for override in (False, True):
                board = "--header_version 4"
                if override:
                    board += " --os_version 0 --os_patch_level 0"
                info = {
                    "mkbootimg_args": board,
                    "mkbootimg_init_args": board,
                    "recovery_mkbootimg_args": board,
                    "mkbootimg_version_args": "--os_version 16 --os_patch_level 2026-10-05",
                    "avb_enable": "true",
                    "avb_avbtool": str(host / "avbtool"),
                    partition + "_size": 1024 * 1024,
                    "avb_" + partition + "_add_hash_footer_args":
                        "--prop com.android.build." + partition + ".os_version:16 "
                        "--prop com.android.build." + partition + ".security_patch:2026-08-05",
                }
                common.OPTIONS.info_dict = info
                os.environ["MKBOOTIMG"] = str(wrapper)
                data = common._BuildBootableImage(
                    partition + ".img", str(source), None, info_dict=info,
                    has_ramdisk=partition != "boot")
                assert header(data) == (4, 0), (partition, override, header(data))
                output = temp / (partition + ".img")
                output.write_bytes(data)
                run(host / "avbtool", "verify_image", "--image", output)
                properties = run(host / "avbtool", "info_image", "--image", output)
                assert b"'16'" in properties and b"'2026-08-05'" in properties
                print(f"PASS releasetools {partition}, explicit zero={override}, AVB preserved")

        # Demonstrate the reverted upstream behavior without the device wrapper.
        os.environ["MKBOOTIMG"] = str(host / "mkbootimg")
        data = common._BuildBootableImage("recovery.img", str(source), None,
                                         info_dict=info, has_ramdisk=True)
        assert header(data)[1] != 0, "Expected original platform-last argument order"
        print("PASS control: unwrapped releasetools reproduces nonzero header")

        for version in (3, 4):
            output = temp / "direct.img"
            run(wrapper, "--header_version=" + str(version), "--kernel", source / "kernel",
                "--os_version", "16", "--os_patch_level", "2026-10-05", "-o", output)
            actual = header(output.read_bytes())
            assert actual[0] == version and (actual[1] == 0) == (version == 4)
        print("PASS direct Make-style calls: v4 zero, v3 unchanged")

        stock_vendor = temp / "stock-vendor.img"
        wrapped_vendor = temp / "wrapped-vendor.img"
        command = ["--header_version", "4", "--vendor_ramdisk", source / "kernel",
                   "--os_version", "16", "--os_patch_level", "2026-10-05"]
        run(host / "mkbootimg", *command, "--vendor_boot", stock_vendor)
        run(wrapper, *command, "--vendor_boot", wrapped_vendor)
        assert stock_vendor.read_bytes() == wrapped_vendor.read_bytes()
        print("PASS vendor_boot passthrough is byte-identical")

        # A temporary executable observes the environment at the standalone
        # release boundary, then uses real mkbootimg to write a v4 image.
        fake_host = temp / "host"
        (fake_host / "bin").mkdir(parents=True)
        (fake_host / "bin/mkbootimg").symlink_to(host / "mkbootimg")
        entry = fake_host / "bin/add_img_to_target_files"
        entry.write_text(
            "#!/usr/bin/env python3\nimport os, subprocess, sys\n"
            "subprocess.check_call([os.environ['MKBOOTIMG'], *sys.argv[1:]])\n")
        entry.chmod(0o755)
        output = temp / "standalone.img"
        run(sys.executable, tools / "run-releasetool.py", "--host-tools", fake_host,
            "add_img_to_target_files", "--header_version", "4",
            "--kernel", source / "kernel", "--os_version", "16",
            "--os_patch_level", "2026-10-05", "--output", output)
        assert header(output.read_bytes()) == (4, 0)
        print("PASS standalone entry point forwards arguments and wrapper environment")
    common.Cleanup()


if __name__ == "__main__":
    main()
