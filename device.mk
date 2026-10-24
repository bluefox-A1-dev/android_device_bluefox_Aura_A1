#
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#

# Project ID Quota
$(call inherit-product, $(SRC_TARGET_DIR)/product/emulated_storage.mk)

# Enforce generic ramdisk allow list
$(call inherit-product, $(SRC_TARGET_DIR)/product/generic_ramdisk.mk)

# A/B
$(call inherit-product, $(SRC_TARGET_DIR)/product/virtual_ab_ota/launch_with_vendor_ramdisk.mk)
PRODUCT_VIRTUAL_AB_COMPRESSION := true

PRODUCT_PACKAGES += \
    android.hardware.boot-service.default_recovery

PRODUCT_PACKAGES += \
    update_engine \
    update_engine_sideload \
    update_verifier

PRODUCT_PACKAGES_DEBUG += \
    update_engine_client

# Audio
PRODUCT_PACKAGES += \
    libbundleaidl \
    libdownmixaidl \
    libdynamicsprocessingaidl \
    liberasersw \
    libextensioneffect \
    libhapticgeneratoraidl \
    libloudnessenhanceraidl \
    libreverbaidl \
    libvisualizeraidl

# Debug
ifneq ($(filter userdebug eng,$(TARGET_BUILD_VARIANT)),)
WITH_ADB_INSECURE := true

PRODUCT_SYSTEM_EXT_PROPERTIES += \
    persist.logd.audit.rate=0 \
    persist.sys.usb.config=adb \
    service.adb.root=1

PRODUCT_PACKAGES += \
    aura_bootlog \
    init.Aura_A1.adb.rc \
    init.Aura_A1.bootlog.rc
endif

# Dynamic Partitions
PRODUCT_USE_DYNAMIC_PARTITIONS := true
PRODUCT_BUILD_SUPER_PARTITION := true

PRODUCT_PACKAGES += \
    fastbootd

# Face
PRODUCT_PACKAGES += \
    AuraFaceEnroll \
    init.Aura_A1.face.rc

# Linker
PRODUCT_VENDOR_LINKER_CONFIG_FRAGMENTS += $(LOCAL_PATH)/configs/linker.config.json

# Overlays
PRODUCT_PACKAGES += \
    FrameworksResOverlayAuraA1 \
    SettingsOverlayAuraA1

PRODUCT_ENFORCE_RRO_TARGETS := *

# Page Size
PRODUCT_MAX_PAGE_SIZE_SUPPORTED := 4096

# Permissions: identical to the stock declarations; use the source modules.
PRODUCT_PACKAGES += \
    android.hardware.audio.low_latency.prebuilt.xml \
    android.hardware.bluetooth_le.prebuilt.xml \
    android.hardware.consumerir.prebuilt.xml \
    android.hardware.faketouch.prebuilt.xml \
    android.hardware.hardware_keystore.xml \
    android.hardware.identity_credential.xml \
    android.hardware.location.gps.prebuilt.xml \
    android.hardware.sensor.accelerometer.prebuilt.xml \
    android.hardware.sensor.compass.prebuilt.xml \
    android.hardware.sensor.gyroscope.prebuilt.xml \
    android.hardware.sensor.hifi_sensors.prebuilt.xml \
    android.hardware.sensor.light.prebuilt.xml \
    android.hardware.sensor.proximity.prebuilt.xml \
    android.hardware.sensor.stepcounter.prebuilt.xml \
    android.hardware.sensor.stepdetector.prebuilt.xml \
    android.hardware.telephony.ims.prebuilt.xml \
    android.hardware.usb.accessory.prebuilt.xml \
    android.hardware.usb.host.prebuilt.xml \
    android.hardware.vulkan.compute-0.prebuilt.xml \
    android.hardware.vulkan.level-1.prebuilt.xml \
    android.hardware.vulkan.version-1_3.prebuilt.xml \
    android.hardware.wifi.passpoint.prebuilt.xml \
    android.software.device_id_attestation.prebuilt.xml \
    android.software.ipsec_tunnels.prebuilt.xml \
    android.software.verified_boot.prebuilt.xml \
    features_com.android.virt.xml \
    handheld_core_hardware.prebuilt.xml

# Rootdir
PRODUCT_PACKAGES += \
    init.recovery.mt6789.rc

PRODUCT_COPY_FILES += \
    $(LOCAL_PATH)/rootdir/etc/fstab.mt6789:$(TARGET_COPY_OUT_VENDOR_RAMDISK)/first_stage_ramdisk/fstab.mt6789

# Shipping API level
PRODUCT_SHIPPING_API_LEVEL := 36

# Soong namespaces
PRODUCT_SOONG_NAMESPACES += \
    $(LOCAL_PATH)

# Source-built android.hardware.drm-service.clearkey
PRODUCT_PACKAGES += \
    android.hardware.drm-service.clearkey

# Source-built android.hardware.health-service.example
PRODUCT_PACKAGES += \
    android.hardware.health-service.example

# Source-built android.hardware.ir-service.example
PRODUCT_PACKAGES += \
    android.hardware.ir-service.example

# Source-built android.hardware.sensors-service.multihal
PRODUCT_PACKAGES += \
    android.hardware.sensors-service.multihal \
    init.Aura_A1.sensors.rc

# Source-built android.hardware.contexthub-service.tinysys
PRODUCT_PACKAGES += \
    android.hardware.contexthub-service.tinysys

# Source-built android.hardware.wifi-service-lazy
PRODUCT_PACKAGES += \
    android.hardware.wifi-service-lazy \
    libwifi-hal-wrapper \
    aura_wifi_hal_mtk_link

# Device-owned platform init scripts. Preserve the OEM installation paths.
PRODUCT_COPY_FILES += $(foreach rc,$(sort \
    $(wildcard $(LOCAL_PATH)/rootdir/etc/init/hw/*.rc) \
    $(LOCAL_PATH)/rootdir/etc/ueventd.rc), \
    $(rc):$(TARGET_COPY_OUT_VENDOR)/$(patsubst $(LOCAL_PATH)/rootdir/%,%,$(rc)))

# Inherit the proprietary files
$(call inherit-product, vendor/bluefox/Aura_A1/Aura_A1-vendor.mk)
