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

# Shipping API level
PRODUCT_SHIPPING_API_LEVEL := 36

# Soong namespaces
PRODUCT_SOONG_NAMESPACES += \
    $(LOCAL_PATH)

# Inherit the proprietary files
$(call inherit-product, vendor/bluefox/Aura_A1/Aura_A1-vendor.mk)
