# Signing and OTA generation

The [boot image header requirements](boot-image-packaging.md) also apply when
release tools rebuild images.

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
