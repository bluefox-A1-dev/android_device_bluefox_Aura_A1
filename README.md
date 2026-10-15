# BLUEFOX Aura A1

LineageOS 23.2 device tree, branched from the Q25 skeleton at `49f5961`.
The vendor and DLKM partitions are built from source modules, necessary hardware blobs and
partition-scoped signed modules. The matched 20260930 GKI and DTB/DTBO remain
prebuilt. SELinux uses the common Lineage MTK policy with device additions.

From a Lineage checkout, prepare a complete stock package and run extract-utils:

```sh
python3 device/bluefox/Aura_A1/prepare-dump.py /path/to/IMAGES --out /path/to/new-dump
PYTHONPATH=tools/extract-utils python3 device/bluefox/Aura_A1/extract-files.py /path/to/new-dump
source build/envsetup.sh
breakfast Aura_A1
```

`prepare-dump.py` also accepts a complete output from `extract/stock.py`.
The proprietary list does not pin blob hashes. Prefer source-built libraries;
private library copies are reserved for demonstrated OEM HAL ABI requirements.
Kernel, DTB/DTBO and modules must be updated together. Keep porting logs outside this device repository.

Source-built AOSP NDK interfaces are used by default. The remaining private
libraries in `configs/private-libraries.json` are hardware compatibility exceptions:

- `android.hardware.camera.common-V2-ndk`: OEM camera HALs require V2, but
  the source tree only freezes V1 and camera device V3 imports V1. Isolate
  the OEM V2 ABI without enabling the unfrozen source version.
- `android.hardware.sensors-V2-ndk`: the OEM `mnld` directly uses V2 while
  `android.frameworks.sensorservice-V1-ndk` pulls in V3. Keep V2 isolated to
  avoid Soong's multiple-version AIDL dependency conflict.
- `android.hardware.bluetooth.audio-V4-ndk`,
  `android.hardware.audio.common-V3-ndk`, `android.hardware.audio.effect-V2-ndk`,
  `android.media.audio.common.types-V3-ndk`: isolate the older audio dependency
  chain used alongside source Bluetooth audio V5/audio common V4/audio types V4.
- `android.hardware.graphics.common-V5-ndk` and
  `android.hardware.graphics.common-V6-ndk`: OEM graphics/camera components use
  these older versions alongside source dependencies importing V7.
- `libtinyxml2`: the OEM PQ, power and audio code uses the older C++ object layout.
- `libaudioutils`, `libvibratorutils`, `chremetrics-cpp`: OEM audio, haptic and
  context-hub components require the matching private ABI.
- `lib_android_keymaster_keymint_utils`, `libkeymaster_messages`,
  `libkeymaster_portable`, `libkeymint`, `libpuresoftkeymasterdevice`: the matched
  Beanpod KeyMint/Keymaster runtime.

Regenerate the inventory from a complete, unmodified stock extraction with
`python3 device/bluefox/Aura_A1/generate-proprietary-files.py /path/to/full-dump`,
then rerun extraction from the prepared staging directory. Source-provided
paths are excluded by `configs/source-provided.json`; private ABI exceptions
have priority over that list. Extraction fixes SONAME and DT_NEEDED only for
these exceptions and retains ELF verification.

## Boot image packaging and OTA

Aura A1 requires header v4 with a zero OS version/patch field in boot and
init_boot. Real OS/SPL values remain in AVB properties. `BOARD_CUSTOM_MKBOOTIMG`
selects `aura_a1_mkbootimg`, which calls the stock tool with final zero-value
arguments for v4 boot-format outputs, before AVB signing. Vendor-boot-only
outputs and older header formats pass through unchanged. The stock tool is a
required host dependency. No build/make patch is needed.

Normal Make image and target-files builds select the wrapper automatically.
For standalone signing, rebuilding images, and generating OTAs, use the device
entry point for **each** operation (Aura A1 target-files only):

```sh
python3 device/bluefox/Aura_A1/tools/run-releasetool.py \
    --host-tools out/host/linux-x86 \
    sign_target_files_apks -o -d /path/to/keys input-target_files.zip signed-target_files.zip
python3 device/bluefox/Aura_A1/tools/run-releasetool.py \
    --host-tools out/host/linux-x86 \
    ota_from_target_files signed-target_files.zip ota.zip
```

`--host-tools` can also point to an extracted otatools directory containing
`bin/`. Keep both Python scripts together when copying them to a release host;
Python 3 is required. The entry point sets `MKBOOTIMG` and selects the stock
tool from that host directory. Running stock releasetools directly bypasses
this policy when images are rebuilt. Existing images reused from target-files
are not rewritten: start with correctly built images and check final artifacts.

Before flashing or release, check that final boot/init_boot headers are v4
with OS version/patch field zero and verify the AVB chain. These packaging
checks do not replace an on-device OTA test.

Host regression check (after building `mkbootimg`, `mkbootfs` and `avbtool`):

```sh
python3 device/bluefox/Aura_A1/tools/test-boot-packaging.py --lineage "$PWD"
```

Run this with the original platform-last releasetools implementation. It
checks real temporary boot/init_boot/recovery images, AVB properties and
hashes, legacy/vendor output passthrough, and the standalone environment.
The unwrapped control must reproduce the nonzero header to demonstrate that
the device wrapper replaces the former build/make ordering patch.
