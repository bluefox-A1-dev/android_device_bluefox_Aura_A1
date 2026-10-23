/*
 * Copyright (C) 2021 The Android Open Source Project
 * SPDX-FileCopyrightText: 2026 The LineageOS Project
 * SPDX-License-Identifier: Apache-2.0
 */

#include <android/binder_interface_utils.h>
#include <health-impl/Health.h>
#include <health/utils.h>

#include <memory>

using aidl::android::hardware::health::HalHealthLoop;
using aidl::android::hardware::health::Health;

int main() {
    auto config = std::make_unique<healthd_config>();
    ::android::hardware::health::InitHealthdConfig(config.get());
    auto health = ndk::SharedRefBase::make<Health>("default", std::move(config));
    return std::make_shared<HalHealthLoop>(health, health)->StartLoop();
}
