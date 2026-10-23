#
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#

# Inherit from those products. Most specific first.
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/full_base_telephony.mk)

# Inherit from device makefile.
$(call inherit-product, device/bluefox/Aura_A1/device.mk)

# Inherit some common LineageOS stuff.
$(call inherit-product, vendor/lineage/config/common_full_phone.mk)

PRODUCT_NAME := lineage_Aura_A1
PRODUCT_DEVICE := Aura_A1
PRODUCT_MANUFACTURER := BLUEFOX
PRODUCT_BRAND := BLUEFOX
PRODUCT_MODEL := BF00A

PRODUCT_BUILD_PROP_OVERRIDES += \
    BuildFingerprint=BLUEFOX/Aura_A1/Aura_A1:16/BP2A.250605.031.A3/20260930:user/release-keys \
    DeviceProduct=Aura_A1
