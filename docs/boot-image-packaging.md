# Boot image packaging

## Header requirements

Aura A1 requires header v4 with a zero OS version/patch field in boot and
init_boot. Real OS/SPL values remain in AVB properties. `BOARD_CUSTOM_MKBOOTIMG`
selects `aura_a1_mkbootimg`, which calls the stock tool with final zero-value
arguments for v4 boot-format outputs, before AVB signing. Vendor-boot-only
outputs and older header formats pass through unchanged. The stock tool is a
required host dependency. No build/make patch is needed.

Normal Make image and target-files builds select the wrapper automatically.
For standalone signing, image rebuilding and OTA generation, follow
[signing and OTA generation](ota.md).

## Host regression check

After building `mkbootimg`, `mkbootfs` and `avbtool`, run:

```sh
python3 device/bluefox/Aura_A1/tools/test-boot-packaging.py --lineage "$PWD"
```

Run this with the original platform-last releasetools implementation. It
checks real temporary boot/init_boot/recovery images, AVB properties and
hashes, legacy/vendor output passthrough, and the standalone environment.
The unwrapped control must reproduce the nonzero header to demonstrate that
the device wrapper replaces the former build/make ordering patch.
