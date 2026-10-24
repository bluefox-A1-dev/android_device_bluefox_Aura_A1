# Proprietary files

## Prepare and extract

From a LineageOS checkout, prepare a complete stock package and run extract-utils:

```sh
python3 device/bluefox/Aura_A1/prepare-dump.py /path/to/IMAGES --out /path/to/new-dump
PYTHONPATH=tools/extract-utils python3 device/bluefox/Aura_A1/extract-files.py /path/to/new-dump
```

`prepare-dump.py` also accepts a complete output from `extract/stock.py`.
The proprietary list does not pin blob hashes. Prefer source-built libraries;
private library copies are reserved for demonstrated OEM HAL ABI requirements.

Continue with [build setup](build.md) after extraction.

## Private ABI compatibility

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

## Regenerate the inventory

Regenerate the inventory from a complete, unmodified stock extraction with
`python3 device/bluefox/Aura_A1/generate-proprietary-files.py /path/to/full-dump`,
then rerun extraction from the prepared staging directory. Source-provided
paths are excluded by `configs/source-provided.json`; private ABI exceptions
have priority over that list. Extraction fixes SONAME and DT_NEEDED only for
these exceptions and retains ELF verification.

## Device-owned platform rc files

Following the Q25 ownership split, platform initialization scripts and ueventd
configuration are maintained in the device tree, while vendor service rc files
remain in `proprietary/vendor/etc/init/` in the vendor repository.

The device tree preserves vendor-relative paths in `rootdir/etc/init/hw/` and
`rootdir/etc/ueventd.rc`; `device.mk` installs them into the same vendor locations.
All 24 platform scripts, including factory/META scripts, retain their original
names, imports and bytes. The migrated `init.project.rc` already includes the
removal of unsupported mmstat trace setup. Device-specific rc modules retain
their existing installation rules.

The inventory generator excludes rc files already present at the corresponding
`rootdir` path. Edit these device-owned files directly rather than adding them
back to `proprietary-files.txt` or applying extraction fixups. The 93 vendor
service rc files remain in the extraction list. Shell scripts and the vendor
fstab retain their existing ownership.
