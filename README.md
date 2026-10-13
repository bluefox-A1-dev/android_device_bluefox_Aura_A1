# BLUEFOX Aura A1

LineageOS 23.2 device tree, branched from the Q25 skeleton at `49f5961`.
The vendor and DLKM partitions are built from pinned file-level stock blobs and
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
The proprietary list pins the stock artifacts; kernel, DTB/DTBO and modules must
be updated together. Keep porting logs outside this device repository.
