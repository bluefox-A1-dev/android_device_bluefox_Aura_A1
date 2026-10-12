#!/usr/bin/env -S PYTHONPATH=../../../tools/extract-utils python3
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0

from extract_utils.main import ExtractUtils, ExtractUtilsModule


def write_prebuilt_board_config(ctx, packages):
    ctx.board_config_mk_out.write('''# Preserve stock HALs, policy, firmware and module metadata as matched images.
BOARD_PREBUILT_VENDORIMAGE := vendor/bluefox/Aura_A1/proprietary/prebuilt/vendor.img
BOARD_PREBUILT_VENDOR_DLKMIMAGE := vendor/bluefox/Aura_A1/proprietary/prebuilt/vendor_dlkm.img
BOARD_PREBUILT_SYSTEM_DLKMIMAGE := vendor/bluefox/Aura_A1/proprietary/prebuilt/system_dlkm.img
BOARD_PREBUILT_ODM_DLKMIMAGE := vendor/bluefox/Aura_A1/proprietary/prebuilt/odm_dlkm.img
''')


module = ExtractUtilsModule('Aura_A1', 'bluefox', namespace_imports=['device/bluefox/Aura_A1'])
module.proprietary_files[0].add_post_makefile_generation_fn(write_prebuilt_board_config)

if __name__ == '__main__':
    ExtractUtils.device(module).run()
