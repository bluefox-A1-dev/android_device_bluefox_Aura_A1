# BLUEFOX Aura A1

LineageOS 23.2 device tree, branched from the Q25 skeleton at `49f5961`.
The first build keeps the matched 20260930 stock vendor/DLKM images and GKI;
Android system, product, system_ext, init_boot and recovery are built from source.

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
