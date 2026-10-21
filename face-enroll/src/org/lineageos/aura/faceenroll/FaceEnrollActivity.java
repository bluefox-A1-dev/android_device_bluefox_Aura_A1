// SPDX-License-Identifier: Apache-2.0
package org.lineageos.aura.faceenroll;

import static android.hardware.biometrics.BiometricFaceConstants.FEATURE_REQUIRE_ATTENTION;
import static android.hardware.biometrics.BiometricFaceConstants.FEATURE_REQUIRE_REQUIRE_DIVERSITY;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.ImageFormat;
import android.graphics.Matrix;
import android.graphics.Rect;
import android.graphics.SurfaceTexture;
import android.hardware.camera2.CameraAccessException;
import android.hardware.camera2.CameraCaptureSession;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraDevice;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.hardware.face.FaceEnrollOptions;
import android.hardware.face.FaceManager;
import android.media.Image;
import android.media.ImageReader;
import android.os.Bundle;
import android.os.CancellationSignal;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.UserHandle;
import android.system.Os;
import android.system.OsConstants;
import android.util.Log;
import android.util.Size;
import android.view.Gravity;
import android.view.Surface;
import android.view.TextureView;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.io.FileDescriptor;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.Arrays;

/** Device-specific producer for the unmodified stock HAL's enrollment file protocol. */
public final class FaceEnrollActivity extends Activity
        implements TextureView.SurfaceTextureListener {
    private static final String TAG = "AuraFaceEnroll";
    private static final int WIDTH = 640;
    private static final int HEIGHT = 480;
    private static final String FRAME = "/data/vendor_de/0/facedata/faceIdEnroll.yuv";
    private static final int REQUEST_CAMERA = 1;
    private final Handler mMain = new Handler();
    private final Object mFrameLock = new Object();
    private final byte[] mNv21 = new byte[WIDTH * HEIGHT * 3 / 2];
    private TextureView mPreview;
    private TextView mStatus;
    private TextView mProgress;
    private Button mButton;
    private HandlerThread mImageThread;
    private Handler mImages;
    private CameraDevice mCamera;
    private CameraCaptureSession mSession;
    private ImageReader mReader;
    private Surface mSurface;
    private FaceManager mFaceManager;
    private CancellationSignal mCancel;
    private byte[] mToken;
    private boolean mResumed;
    private boolean mOpening;
    private boolean mTerminal;
    private boolean mStarted;
    private boolean mSubmittedFrame;
    private boolean mTouchedFrame;
    private volatile boolean mFeed;
    private int mSensorOrientation;
    private final Runnable mTimeout =
            () -> {
                if (!mTerminal)
                    fail(R.string.failed, new IllegalStateException("Enrollment timeout"));
            };

    @Override
    public void onCreate(Bundle state) {
        super.onCreate(state);
        setResult(RESULT_CANCELED);
        getWindow()
                .addFlags(
                        WindowManager.LayoutParams.FLAG_SECURE
                                | WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        buildUi();
        // The entry point is signature-protected and only accepts Settings' credential flow.
        if (!"com.android.settings".equals(getCallingPackage()) || state != null) {
            finish();
            return;
        }
        int user = getIntent().getIntExtra(Intent.EXTRA_USER_ID, UserHandle.myUserId());
        if (user != 0 || UserHandle.myUserId() != 0) {
            fail(R.string.owner_only, null);
            return;
        }
        mToken = getIntent().getByteArrayExtra("hw_auth_token");
        mFaceManager = getSystemService(FaceManager.class);
        if (mToken == null || mToken.length == 0 || mFaceManager == null) {
            fail(R.string.failed, null);
            return;
        }
        mImageThread = new HandlerThread("AuraFaceFrames");
        mImageThread.start();
        mImages = new Handler(mImageThread.getLooper());
        mPreview.setSurfaceTextureListener(this);
    }

    private void buildUi() {
        int padding = (int) (24 * getResources().getDisplayMetrics().density);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setGravity(Gravity.CENTER_HORIZONTAL);
        layout.setPadding(padding, padding * 2, padding, padding);
        layout.setFitsSystemWindows(true);
        TextView title = new TextView(this);
        title.setText(R.string.title);
        title.setTextSize(26);
        layout.addView(title);
        mStatus = new TextView(this);
        mStatus.setText(R.string.starting);
        mStatus.setTextSize(18);
        mStatus.setGravity(Gravity.CENTER);
        mStatus.setPadding(0, padding, 0, padding);
        layout.addView(mStatus);
        mPreview = new TextureView(this);
        layout.addView(
                mPreview,
                new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1));
        mProgress = new TextView(this);
        mProgress.setPadding(0, padding, 0, padding);
        layout.addView(mProgress);
        mButton = new Button(this);
        mButton.setText(R.string.cancel);
        mButton.setOnClickListener(v -> finish());
        layout.addView(mButton);
        setContentView(layout);
    }

    @Override
    public void onResume() {
        super.onResume();
        mResumed = true;
        if (mTerminal || isFinishing()) return;
        if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[] {Manifest.permission.CAMERA}, REQUEST_CAMERA);
        } else if (mPreview.isAvailable()) {
            openCamera();
        }
    }

    @Override
    public void onRequestPermissionsResult(int request, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(request, permissions, results);
        if (request != REQUEST_CAMERA || mTerminal) return;
        if (results.length != 1 || results[0] != PackageManager.PERMISSION_GRANTED) {
            fail(R.string.camera_failed, null);
        } else if (mResumed && mPreview.isAvailable()) {
            openCamera();
        }
    }

    private void openCamera() {
        if (!mResumed
                || mTerminal
                || mOpening
                || mCamera != null
                || mImages == null
                || checkSelfPermission(Manifest.permission.CAMERA)
                        != PackageManager.PERMISSION_GRANTED) {
            return;
        }
        CameraManager manager = getSystemService(CameraManager.class);
        try {
            for (String id : manager.getCameraIdList()) {
                CameraCharacteristics c = manager.getCameraCharacteristics(id);
                Integer facing = c.get(CameraCharacteristics.LENS_FACING);
                if (facing == null || facing != CameraCharacteristics.LENS_FACING_FRONT) continue;
                StreamConfigurationMap map =
                        c.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP);
                if (map == null
                        || !supportsVga(map.getOutputSizes(ImageFormat.YUV_420_888))
                        || !supportsVga(map.getOutputSizes(SurfaceTexture.class))) continue;
                Integer orientation = c.get(CameraCharacteristics.SENSOR_ORIENTATION);
                mSensorOrientation = orientation == null ? 0 : orientation;
                mOpening = true;
                manager.openCamera(
                        id,
                        new CameraDevice.StateCallback() {
                            @Override
                            public void onOpened(CameraDevice camera) {
                                mOpening = false;
                                if (!mResumed || mTerminal) {
                                    camera.close();
                                    return;
                                }
                                mCamera = camera;
                                configureCamera();
                            }

                            @Override
                            public void onDisconnected(CameraDevice camera) {
                                camera.close();
                                mOpening = false;
                                if (!mTerminal) fail(R.string.camera_failed, null);
                            }

                            @Override
                            public void onError(CameraDevice camera, int error) {
                                camera.close();
                                mOpening = false;
                                if (!mTerminal)
                                    fail(
                                            R.string.camera_failed,
                                            new IllegalStateException("Camera error " + error));
                            }
                        },
                        mMain);
                return;
            }
            fail(R.string.camera_failed, new IllegalStateException("No front VGA YUV camera"));
        } catch (CameraAccessException | RuntimeException e) {
            fail(R.string.camera_failed, e);
        }
    }

    private static boolean supportsVga(Size[] sizes) {
        return sizes != null && Arrays.asList(sizes).contains(new Size(WIDTH, HEIGHT));
    }

    private void configureCamera() {
        try {
            SurfaceTexture texture = mPreview.getSurfaceTexture();
            if (texture == null) {
                fail(R.string.camera_failed, null);
                return;
            }
            texture.setDefaultBufferSize(WIDTH, HEIGHT);
            transformPreview();
            mSurface = new Surface(texture);
            mReader = ImageReader.newInstance(WIDTH, HEIGHT, ImageFormat.YUV_420_888, 2);
            mReader.setOnImageAvailableListener(this::onImage, mImages);
            CaptureRequest.Builder request =
                    mCamera.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW);
            request.addTarget(mSurface);
            request.addTarget(mReader.getSurface());
            mCamera.createCaptureSession(
                    Arrays.asList(mSurface, mReader.getSurface()),
                    new CameraCaptureSession.StateCallback() {
                        @Override
                        public void onConfigured(CameraCaptureSession session) {
                            if (!mResumed || mTerminal || mCamera == null) {
                                session.close();
                                return;
                            }
                            mSession = session;
                            try {
                                session.setRepeatingRequest(request.build(), null, mMain);
                                startEnrollment();
                            } catch (CameraAccessException | RuntimeException e) {
                                fail(R.string.camera_failed, e);
                            }
                        }

                        @Override
                        public void onConfigureFailed(CameraCaptureSession session) {
                            session.close();
                            if (!mTerminal) fail(R.string.camera_failed, null);
                        }
                    },
                    mMain);
        } catch (CameraAccessException | RuntimeException e) {
            fail(R.string.camera_failed, e);
        }
    }

    private void startEnrollment() {
        if (mStarted || mTerminal) return;
        mStarted = true;
        mCancel = new CancellationSignal();
        ArrayList<Integer> disabled = new ArrayList<>();
        if (!getIntent().getBooleanExtra("accessibility_diversity", true)) {
            disabled.add(FEATURE_REQUIRE_REQUIRE_DIVERSITY);
        }
        if (!getIntent().getBooleanExtra("accessibility_vision", true)) {
            disabled.add(FEATURE_REQUIRE_ATTENTION);
        }
        int[] features = disabled.stream().mapToInt(Integer::intValue).toArray();
        try {
            mFaceManager.enroll(
                    0,
                    mToken,
                    mCancel,
                    new FaceManager.EnrollmentCallback() {
                        @Override
                        public void onEnrollmentProgress(int remaining) {
                            if (mTerminal) return;
                            Log.i(TAG, "Enrollment remaining=" + remaining);
                            if (remaining == 0) {
                                mTerminal = true;
                                // Match Settings' RESULT_FINISHED. Its education/introduction flow
                                // propagates this result to SUW and multi-biometric enrollment.
                                setResult(
                                        RESULT_FIRST_USER,
                                        new Intent().putExtra("finished_enrolling_face", true));
                                stopCapture(false);
                                mStatus.setText(R.string.done);
                                mProgress.setText("");
                                mButton.setText(R.string.close);
                            } else {
                                // Stock HAL emits an initial remaining=3 after clearing the file.
                                mFeed = true;
                                mStatus.setText(R.string.guidance);
                                mProgress.setText(getString(R.string.progress, remaining));
                            }
                        }

                        @Override
                        public void onEnrollmentHelp(int code, CharSequence message) {
                            if (!mTerminal && message != null) mStatus.setText(message);
                        }

                        @Override
                        public void onEnrollmentError(int code, CharSequence message) {
                            if (mTerminal) return;
                            fail(R.string.failed, new IllegalStateException("Face error " + code));
                            if (message != null) mStatus.setText(message);
                        }
                    },
                    features,
                    null,
                    false,
                    new FaceEnrollOptions.Builder().setEnrollReason(enrollReason()).build());
            mMain.postDelayed(mTimeout, 80000);
        } catch (RuntimeException e) {
            fail(R.string.failed, e);
        } finally {
            Arrays.fill(mToken, (byte) 0);
            mToken = null;
            getIntent().removeExtra("hw_auth_token");
        }
    }

    private int enrollReason() {
        int reason =
                getIntent().getIntExtra("enroll_reason", FaceEnrollOptions.ENROLL_REASON_SETTINGS);
        return reason >= FaceEnrollOptions.ENROLL_REASON_UNKNOWN
                        && reason <= FaceEnrollOptions.ENROLL_REASON_SUW
                ? reason
                : FaceEnrollOptions.ENROLL_REASON_UNKNOWN;
    }

    private void onImage(ImageReader reader) {
        synchronized (mFrameLock) {
            try (Image image = reader.acquireLatestImage()) {
                if (image == null || !mFeed) return;
                // HAL owns/creates the file. Never create a substitute or touch templates.
                if (Os.stat(FRAME).st_size != 0) return;
                Rect crop = image.getCropRect();
                if (image.getFormat() != ImageFormat.YUV_420_888
                        || crop.width() != WIDTH
                        || crop.height() != HEIGHT) {
                    throw new IllegalStateException("Unexpected enrollment image size/format");
                }
                Image.Plane[] p = image.getPlanes();
                Nv21.pack(
                        WIDTH,
                        HEIGHT,
                        crop.left,
                        crop.top,
                        new ByteBuffer[] {p[0].getBuffer(), p[1].getBuffer(), p[2].getBuffer()},
                        new int[] {p[0].getRowStride(), p[1].getRowStride(), p[2].getRowStride()},
                        new int[] {
                            p[0].getPixelStride(), p[1].getPixelStride(), p[2].getPixelStride()
                        },
                        mNv21);
                FileDescriptor fd =
                        Os.open(
                                FRAME,
                                OsConstants.O_WRONLY
                                        | OsConstants.O_NOFOLLOW
                                        | OsConstants.O_CLOEXEC,
                                0);
                mTouchedFrame = true;
                try {
                    int offset = 0;
                    while (offset < mNv21.length) {
                        int written = Os.write(fd, mNv21, offset, mNv21.length - offset);
                        if (written <= 0) throw new IllegalStateException("Short frame write");
                        offset += written;
                    }
                } finally {
                    Os.close(fd);
                }
                if (!mSubmittedFrame) {
                    mSubmittedFrame = true;
                    Log.i(TAG, "Submitted first 640x480 NV21 enrollment frame");
                }
            } catch (Exception e) {
                if (mFeed) {
                    mFeed = false;
                    mMain.post(
                            () -> {
                                if (!mTerminal) fail(R.string.frame_failed, e);
                            });
                }
            }
        }
    }

    private void transformPreview() {
        float w = mPreview.getWidth(), h = mPreview.getHeight();
        if (w == 0 || h == 0) return;
        // TextureView initially stretches the 640x480 buffer to its bounds.
        // Undo that stretch, rotate into portrait, fit, then mirror for a selfie preview.
        boolean swap = mSensorOrientation % 180 != 0;
        float scale = Math.min(w / (swap ? HEIGHT : WIDTH), h / (swap ? WIDTH : HEIGHT));
        Matrix matrix = new Matrix();
        matrix.setScale(WIDTH / w, HEIGHT / h, w / 2, h / 2);
        matrix.postRotate(mSensorOrientation, w / 2, h / 2);
        matrix.postScale(-scale, scale, w / 2, h / 2);
        mPreview.setTransform(matrix);
    }

    private void fail(int message, Exception e) {
        if (mTerminal) return;
        Log.e(TAG, "Enrollment stopped", e);
        mTerminal = true;
        stopCapture(true);
        mStatus.setText(message);
        mProgress.setText("");
    }

    private void stopCapture(boolean cancel) {
        mFeed = false;
        mMain.removeCallbacks(mTimeout);
        if (cancel && mCancel != null) mCancel.cancel();
        mCancel = null;
        if (mSession != null) {
            mSession.close();
            mSession = null;
        }
        if (mCamera != null) {
            mCamera.close();
            mCamera = null;
        }
        synchronized (mFrameLock) {
            if (mReader != null) {
                mReader.close();
                mReader = null;
            }
            if (mTouchedFrame) {
                try {
                    FileDescriptor fd =
                            Os.open(
                                    FRAME,
                                    OsConstants.O_WRONLY
                                            | OsConstants.O_NOFOLLOW
                                            | OsConstants.O_CLOEXEC,
                                    0);
                    try {
                        Os.ftruncate(fd, 0);
                    } finally {
                        Os.close(fd);
                    }
                } catch (Exception e) {
                    Log.w(TAG, "Cannot clear enrollment frame", e);
                }
                mTouchedFrame = false;
                mSubmittedFrame = false;
            }
            Arrays.fill(mNv21, (byte) 0);
        }
        if (mSurface != null) {
            mSurface.release();
            mSurface = null;
        }
        mPreview.setVisibility(View.INVISIBLE);
        getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
    }

    @Override
    public void onPause() {
        mResumed = false;
        // Permission dialogs happen before opening the camera; do not abandon those.
        if (mStarted || mOpening || mCamera != null) {
            if (!mTerminal) {
                mTerminal = true;
                finish();
            }
            stopCapture(true);
        }
        super.onPause();
    }

    @Override
    public void onDestroy() {
        mTerminal = true;
        stopCapture(true);
        if (mToken != null) Arrays.fill(mToken, (byte) 0);
        if (mImageThread != null) mImageThread.quitSafely();
        super.onDestroy();
    }

    @Override
    public void onSurfaceTextureAvailable(SurfaceTexture t, int w, int h) {
        openCamera();
    }

    @Override
    public void onSurfaceTextureSizeChanged(SurfaceTexture t, int w, int h) {
        transformPreview();
    }

    @Override
    public boolean onSurfaceTextureDestroyed(SurfaceTexture t) {
        return true;
    }

    @Override
    public void onSurfaceTextureUpdated(SurfaceTexture t) {}
}
