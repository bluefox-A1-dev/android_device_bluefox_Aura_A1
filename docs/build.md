# Build setup

LineageOS 23.2 device tree, branched from the Q25 skeleton at `49f5961`.
The vendor and DLKM partitions are built from source modules, necessary hardware blobs and
partition-scoped signed modules. The matched 20260930 GKI and DTB/DTBO remain
prebuilt. SELinux uses the common Lineage MTK policy with device additions.

The kernel, DTB/DTBO and modules must be updated together.

First [extract the proprietary files](proprietary-files.md) from a complete stock
package. Then initialize the build environment from the LineageOS checkout:

```sh
source build/envsetup.sh
breakfast Aura_A1
```

See [boot image packaging](boot-image-packaging.md) for device-specific image
requirements, and [signing and OTA generation](ota.md) for release tooling.
