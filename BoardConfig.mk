#
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#

DEVICE_PATH := device/bluefox/Aura_A1

# Architecture: stock supports both arm64 and 32-bit ARM applications.
TARGET_ARCH := arm64
TARGET_ARCH_VARIANT := armv8-2a
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_ABI2 :=
TARGET_CPU_VARIANT := generic
TARGET_CPU_VARIANT_RUNTIME := cortex-a76
TARGET_2ND_ARCH := arm
TARGET_2ND_ARCH_VARIANT := armv8-2a
TARGET_2ND_CPU_ABI := armeabi-v7a
TARGET_2ND_CPU_ABI2 := armeabi
TARGET_2ND_CPU_VARIANT := generic
TARGET_2ND_CPU_VARIANT_RUNTIME := cortex-a55

TARGET_BOARD_PLATFORM := mt6789
TARGET_SCREEN_DENSITY := 320

# Bootloader and physical partitions (stock scatter, shared by both slots).
TARGET_BOOTLOADER_BOARD_NAME := k6789v1_64
TARGET_NO_BOOTLOADER := true
TARGET_OTA_ASSERT_DEVICE := Aura_A1,k6789v1_64
TARGET_BOARD_INFO_FILE := $(DEVICE_PATH)/board-info.txt
TARGET_BOARD_FASTBOOT_INFO_FILE := $(DEVICE_PATH)/fastboot-info.txt
BOARD_BOOTIMAGE_PARTITION_SIZE := 67108864
BOARD_VENDOR_BOOTIMAGE_PARTITION_SIZE := 67108864
BOARD_INIT_BOOT_IMAGE_PARTITION_SIZE := 8388608
BOARD_DTBOIMG_PARTITION_SIZE := 8388608
BOARD_FLASH_BLOCK_SIZE := 131072
BOARD_USES_METADATA_PARTITION := true

# Dynamic partitions: Virtual A/B can allocate almost the entire super to a slot.
BOARD_SUPER_PARTITION_SIZE := 9663676416
BOARD_SUPER_PARTITION_GROUPS := main
BOARD_MAIN_SIZE := 9661579264
BOARD_MAIN_PARTITION_LIST := odm_dlkm product system system_dlkm system_ext vendor vendor_dlkm
BOARD_SUPER_IMAGE_IN_UPDATE_PACKAGE := true

BOARD_SYSTEMIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_PRODUCTIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_SYSTEM_EXTIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_SYSTEM_DLKMIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_VENDOR_DLKMIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_ODM_DLKMIMAGE_FILE_SYSTEM_TYPE := erofs
TARGET_COPY_OUT_PRODUCT := product
TARGET_COPY_OUT_SYSTEM_EXT := system_ext
TARGET_COPY_OUT_VENDOR := vendor
TARGET_COPY_OUT_SYSTEM_DLKM := system_dlkm
TARGET_COPY_OUT_VENDOR_DLKM := vendor_dlkm
TARGET_COPY_OUT_ODM_DLKM := odm_dlkm
TARGET_USERIMAGES_USE_EXT4 := true
TARGET_USERIMAGES_USE_F2FS := true

# Virtual A/B OTA partitions (including generic ramdisk and GKI modules).
AB_OTA_UPDATER := true
AB_OTA_PARTITIONS += boot init_boot dtbo vendor_boot vbmeta vbmeta_system vbmeta_vendor \
    system product system_ext system_dlkm vendor vendor_dlkm odm_dlkm

# Boot/init_boot/vendor_boot v4, with the stock 4K GKI payload.
BOARD_BOOT_HEADER_VERSION := 4
BOARD_USES_GENERIC_KERNEL_IMAGE := true
BOARD_KERNEL_PAGESIZE := 4096
BOARD_KERNEL_BASE := 0x00000000
BOARD_KERNEL_OFFSET := 0x40000000
BOARD_RAMDISK_OFFSET := 0x66f00000
BOARD_KERNEL_TAGS_OFFSET := 0x47c80000
BOARD_DTB_OFFSET := 0x47c80000
BOARD_KERNEL_CMDLINE := bootopt=64S3,32S1,32S1 bootconfig
BOARD_RAMDISK_USE_LZ4 := true
BOARD_KERNEL_IMAGE_NAME := Image.lz4
TARGET_KERNEL_ARCH := arm64
TARGET_KERNEL_VERSION := 6.12
TARGET_PREBUILT_KERNEL := vendor/bluefox/Aura_A1/proprietary/prebuilt/kernel/Image.lz4
BOARD_INCLUDE_DTB_IN_BOOTIMG := true
BOARD_PREBUILT_DTBIMAGE_DIR := vendor/bluefox/Aura_A1/proprietary/prebuilt/kernel/dtb
BOARD_KERNEL_SEPARATED_DTBO := true
BOARD_PREBUILT_DTBOIMAGE := vendor/bluefox/Aura_A1/proprietary/prebuilt/kernel/dtbo.img
BOARD_MKBOOTIMG_ARGS += --header_version $(BOARD_BOOT_HEADER_VERSION)
BOARD_MKBOOTIMG_ARGS += --kernel_offset $(BOARD_KERNEL_OFFSET)
BOARD_MKBOOTIMG_ARGS += --ramdisk_offset $(BOARD_RAMDISK_OFFSET)
BOARD_MKBOOTIMG_ARGS += --tags_offset $(BOARD_KERNEL_TAGS_OFFSET)
BOARD_MKBOOTIMG_ARGS += --dtb_offset $(BOARD_DTB_OFFSET)
BOARD_BOOTCONFIG += kernel.rcu_nocbs=all
BOARD_BOOTCONFIG += kernel.rcutree.enable_rcu_lazy=1
BOARD_BOOTCONFIG += kernel.rcupdate.rcu_cpu_stall_cputime=1

# Inherit the proprietary files
include vendor/bluefox/Aura_A1/BoardConfigVendor.mk
