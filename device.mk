#
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#

# Preserve the heap tuning in the prebuilt stock vendor properties.
$(call inherit-product, $(SRC_TARGET_DIR)/product/emulated_storage.mk)

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

# Shipping API level
PRODUCT_SHIPPING_API_LEVEL := 36

# Soong namespaces
PRODUCT_SOONG_NAMESPACES += \
    $(LOCAL_PATH)

# Inherit the proprietary files
$(call inherit-product, vendor/bluefox/Aura_A1/Aura_A1-vendor.mk)
