#!/usr/bin/env -S PYTHONPATH=../../../tools/extract-utils python3
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
import json
import hashlib
import re
from pathlib import Path

from extract_utils.bp_builder import BpBuilder
from extract_utils.bp_encoder import BpJSONEncoder
from extract_utils.fixups_blob import blob_fixup
from extract_utils.main import ExtractUtils, ExtractUtilsModule

config = json.loads((Path(__file__).resolve().parent/'configs/vendor-files.json').read_text())


def vendor_library_name(lib, partition, *args, **kwargs):
    if partition == 'vendor' and lib in config['libraries']:
        return lib+'_aura_vendor'
    return None


def write_vendor_metadata(ctx, packages):
    encoder = BpJSONEncoder(legacy=ctx.legacy)
    extra = []
    for entry in config['symlinks']:
        path = entry['path'].removeprefix('vendor/')
        name = 'aura_link_'+re.sub(r'[^a-zA-Z0-9_]','_',path)+'_'+hashlib.sha1(path.encode()).hexdigest()[:8]
        (BpBuilder(encoder).set_rule_name('install_symlink').name(name)
         .set('vendor',True).set('installed_location',path)
         .set('symlink_target',entry['target']).write(ctx.bp_out))
        extra.append(name)
    for entry in config['special']:
        path = entry['path']; filename = Path(path).name
        name = 'aura_stock_'+path.replace('/','_').replace('.','_')
        builder = BpBuilder(encoder).name(name).set('vendor',True)
        if entry['kind'] == 'apex':
            builder.set_rule_name('prebuilt_apex').set('src','proprietary/'+path)
            builder.set('filename',filename.replace('.apex','.aura.apex')).set('prefer',True)
            if filename == 'com.android.hardware.cas.apex':
                builder.set('overrides',['com.android.hardware.cas'])
        elif entry['kind'] == 'overlay':
            # Make supports presigned prebuilt RROs at their original overlay path.
            ctx.mk_out.write(f"""
include $(CLEAR_VARS)
LOCAL_MODULE := {name}
LOCAL_MODULE_CLASS := APPS
LOCAL_SRC_FILES := proprietary/{path}
LOCAL_MODULE_PATH := $(TARGET_OUT_VENDOR)/{str(Path(path).parent).removeprefix('vendor/')}
LOCAL_MODULE_STEM := {Path(filename).stem}
LOCAL_INSTALLED_MODULE_STEM := {filename}
LOCAL_MODULE_SUFFIX := .apk
LOCAL_CERTIFICATE := PRESIGNED
LOCAL_DEX_PREOPT := false
LOCAL_REPLACE_PREBUILT_APK_INSTALLED := $(LOCAL_PATH)/proprietary/{path}
include $(BUILD_PREBUILT)
""")
            extra.append(name)
            continue
        else:
            builder.set_rule_name('android_app_import').set('apk','proprietary/'+path)
            builder.set('filename',filename).set('presigned',True).set('preprocessed',True)
            builder.set('install_path_skip_module_dir',True)
            builder.set('relative_install_path',str(Path(path).parent).removeprefix('vendor/app/'))
            builder.set('dex_preopt',{'enabled':False})
        builder.write(ctx.bp_out);extra.append(name)
    ctx.product_mk_out.write('\nPRODUCT_PACKAGES += \\\n    '+' \\\n    '.join(extra)+'\n')
    ctx.board_config_mk_out.write('''# All runtime partitions are built from files. Kernel payloads remain prebuilt.
DEVICE_MANIFEST_FILE := $(wildcard vendor/bluefox/Aura_A1/proprietary/vendor/etc/vintf/manifest.xml) \\
    $(wildcard vendor/bluefox/Aura_A1/proprietary/vendor/etc/vintf/manifest/*.xml)
DEVICE_MATRIX_FILE := vendor/bluefox/Aura_A1/proprietary/vendor/etc/vintf/compatibility_matrix.xml
''')


blob_fixups = {}
for path,replacements in config.get('needed_fixups',{}).items():
    fixup = blob_fixup()
    for old,new in replacements: fixup.replace_needed(old,new)
    blob_fixups[path] = fixup
for path,replacements in config.get('text_fixups',{}).items():
    fixup = blob_fixup()
    for old,new in replacements: fixup.regex_replace(re.escape(old)+r'(?:_aura)*(?![\w.-])',new)
    blob_fixups[path] = fixup

module = ExtractUtilsModule('Aura_A1','bluefox',
    blob_fixups=blob_fixups,
    lib_fixups={tuple(config['libraries']):vendor_library_name},
    namespace_imports=['device/bluefox/Aura_A1','hardware/mediatek'])
module.proprietary_files[0].add_post_makefile_generation_fn(write_vendor_metadata)

if __name__ == '__main__':ExtractUtils.device(module).run()
