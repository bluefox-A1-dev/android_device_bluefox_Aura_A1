# Stock face enrollment adapter

The Aura A1 stock Face HAL has different image paths for enrollment and
verification. Verification opens its own camera. Enrollment instead polls
`/data/vendor_de/<user>/facedata/faceIdEnroll.yuv` and only processes a file of
exactly 460800 bytes (640 × 480 NV21). It truncates the file after consuming it.

The stock CJzhkSettings `com.elephanttek.faceapi.FaceEnrollApi` adds a 640 × 480
`YUV_420_888` ImageReader to the preview capture session. Its frame writer packs
Y, V, U without rotating or mirroring, and writes only when the file is empty.
Lineage Settings' `FaceEnrollPreviewFragment` only configures the display
Surface, so the stock HAL repeatedly logs `face_enroll_timer no yuv`.

Evidence: `lineage-debug/face-unlock-fail-1/face_unlock_fail.txt` in the analysis
workspace, lines 27668–27676 (enrollment), 28232 (camera streaming), and 29308
onwards (missing enrollment frames). This file is UTF-16 LE. The stock HAL and
Settings APK were inspected offline; their authentication and license checks
have not been patched.

Inspected stock SHA-256 values:

- `vendor/lib64/hw/face.default.so`: `7edc4a595066443baaca25914462b8eca64f626ae3587becaf095d2384fb8559`
- `system_ext/priv-app/CJzhkSettings/CJzhkSettings.apk`: `b756655c6d2648b30a3cc9cb8175f31980209d8f3b6abaad2516fe2655a2a338`

## Device-side implementation

- `SettingsOverlayAuraA1` sets Settings' existing `config_face_enroll` component
  to `org.lineageos.aura.faceenroll/.FaceEnrollActivity`.
- `AuraFaceEnroll` uses the Settings-supplied hardware authentication token and
  standard FaceManager enrollment callbacks. It configures both a preview and
  a 640 × 480 ImageReader, and implements the stock empty-file handoff.
- The app is platform-signed, shares the system UID (the HAL's files are owned
  by system), and requires the signature-level MANAGE_BIOMETRIC permission to
  launch. It additionally checks the calling package is Settings.
- A filename-specific SELinux label and HAL type transition allow system_app
  to write only the temporary frame, not face template files. Existing owner
  files are relabeled by an init post-fs-data action. No permissive domain or
  neverallow exemption is added. As with other system-UID applications, this
  is a shared trust boundary, not a separate per-app SELinux sandbox.
- Cancel/background/error closes the camera, stops enrollment, clears frame
  data and discards the token. Success is accepted only on the framework's
  `remaining == 0` callback and returned as Settings' RESULT_FINISHED.

This first implementation deliberately supports **user 0 only**. Secondary
users are rejected explicitly: their app UID and the stock HAL's system-owned
file access need separate validation. It requires the front camera to support
640 × 480 for both preview and YUV. It does not alter the stock matching,
attention, liveness, licensing, or lockout implementation.

## Build and device validation

From the Lineage checkout after `source build/envsetup.sh` and
`breakfast Aura_A1`:

```sh
m AuraFaceEnroll SettingsOverlayAuraA1 selinux_policy
```

Install through a normal rebuilt ROM/OTA: this change includes a system_ext
APK/init file, a product RRO, and vendor SELinux policy. Installing just the
APK is insufficient. No automatic flashing is performed by the adapter.

After reboot, check the selected component:

```sh
adb shell cmd overlay lookup com.android.settings com.android.settings:string/config_face_enroll
adb shell ls -lZ /data/vendor_de/0/facedata/faceIdEnroll.yuv
adb logcat -b all -v threadtime 'AuraFaceEnroll:I' 'FaceHalHW:V' 'FaceHalService:V' '*:S'
```

The file may not exist until Face HAL creates a user session. Its expected
label is `u:object_r:vendor_aura_face_frame:s0`. Start face enrollment from
Settings after confirming the lock-screen credential. Expect:

1. The device enrollment page and front camera preview open.
2. `AuraFaceEnroll: Submitted first 640x480 NV21 enrollment frame` appears.
3. `FaceHalHW: face_enroll_timer, type:...` or real algorithm quality/detection
   feedback replaces the repeated `no yuv` messages.
4. Framework enrollment reaches remaining=0, the page says Face added, and
   Settings reports an enrolled face.
5. Lock-screen face verification works; cancellation/background/re-entry and
   removal/re-enrollment work; a different person is rejected.

Test with SELinux enforcing. If frames cannot be submitted, collect `logcat -b
all` and AVCs, checking the file's label first. If frames are accepted but the
algorithm rejects them, investigate lighting, sensor orientation, and stock
algorithm feedback separately. Do not weaken authentication to make the UI
complete. This adapter addresses missing enrollment input; actual biometric
accuracy and lock-screen verification require hardware testing.

## Host conversion test

```sh
FACE_TEST_OUT=$(mktemp -d)
javac -d "$FACE_TEST_OUT" \
  device/bluefox/Aura_A1/face-enroll/src/org/lineageos/aura/faceenroll/Nv21.java \
  device/bluefox/Aura_A1/face-enroll/tests/Nv21Test.java
java -cp "$FACE_TEST_OUT" org.lineageos.aura.faceenroll.Nv21Test
```

The test covers planar/interleaved chroma, row padding, nonzero buffer positions,
crop offsets, NV21 V/U ordering, and rejection of invalid or truncated planes.

## Validation performed (2026-10-22)

- NV21 host tests passed.
- Both signed APKs built against the current LineageOS 23.2 checkout.
- `selinux_policy` completed, including neverallow, context, sepolicy and device
  type tests. The generated vendor policy includes the named file transition
  and the temporary-frame-only system_app permissions.
- Host `idmap2 create` against the built Settings APK succeeded with the
  signature/product policies (without ignoring overlayable checks), mapping
  `string/config_face_enroll` to the adapter component.
- Settings and frameworks/base source worktrees remain unchanged.

Soong dependency generation was run with an 18 GiB Go memory limit to avoid
host swap pressure; APK and policy targets were then built through the generated
Ninja graph. A full ROM/OTA was not built or flashed. No phone was attached, so
camera preview orientation, successful enrollment, cancellation/re-entry and
lock-screen verification are still unverified on hardware.
