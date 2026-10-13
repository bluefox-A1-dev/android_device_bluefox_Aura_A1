#
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#

# Hardware tuning is kept in vendor.prop.
$(call inherit-product, $(SRC_TARGET_DIR)/product/emulated_storage.mk)

# Preserve the stock vendor library export through the generated linker config.
PRODUCT_VENDOR_LINKER_CONFIG_FRAGMENTS += $(LOCAL_PATH)/configs/linker.config.json

# The matched stock GKI is 4K; some OEM utilities also have 4K ELF alignment.
PRODUCT_MAX_PAGE_SIZE_SUPPORTED := 4096

# First-boot debugging: consumed by Lineage common.mk after this device file.
ifneq ($(filter userdebug eng,$(TARGET_BUILD_VARIANT)),)
WITH_ADB_INSECURE := true
PRODUCT_SYSTEM_EXT_PROPERTIES += persist.sys.usb.config=adb
PRODUCT_PACKAGES += init.Aura_A1.adb.rc
PRODUCT_PACKAGES += aura_bootlog init.Aura_A1.bootlog.rc
endif

# Dynamic partitions
PRODUCT_USE_DYNAMIC_PARTITIONS := true
PRODUCT_BUILD_SUPER_PARTITION := true
PRODUCT_PACKAGES += fastbootd

# Virtual A/B with compressed userspace snapshots, as on stock.
$(call inherit-product, $(SRC_TARGET_DIR)/product/virtual_ab_ota/launch_with_vendor_ramdisk.mk)
PRODUCT_VIRTUAL_AB_COMPRESSION := true
PRODUCT_PACKAGES += update_engine update_engine_sideload update_verifier
PRODUCT_PACKAGES_DEBUG += update_engine_client

# The generic ramdisk lives in init_boot, separate from the GKI boot image.
$(call inherit-product, $(SRC_TARGET_DIR)/product/generic_ramdisk.mk)

# Recovery/fastbootd uses the generic recovery boot HAL, not a second Android HAL.
PRODUCT_PACKAGES += \
    android.hardware.boot-service.default_recovery \
    init.recovery.mt6789.rc

# Preserve the stock phone UI flags; display/brightness overlays stay in vendor.
PRODUCT_PACKAGES += FrameworksResOverlayAuraA1
PRODUCT_ENFORCE_RRO_TARGETS := *

# First-stage fstab and vendor fstab use the same original mount/FBE settings.
PRODUCT_COPY_FILES += \
    $(LOCAL_PATH)/rootdir/etc/fstab.mt6789:$(TARGET_COPY_OUT_VENDOR_RAMDISK)/first_stage_ramdisk/fstab.mt6789

# Shipping API level
PRODUCT_SHIPPING_API_LEVEL := 36

# Soong namespaces
PRODUCT_SOONG_NAMESPACES += \
    $(LOCAL_PATH)

# Inherit the proprietary files
$(call inherit-product, vendor/bluefox/Aura_A1/Aura_A1-vendor.mk)
