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
