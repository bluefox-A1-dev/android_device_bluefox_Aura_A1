// SPDX-License-Identifier: Apache-2.0
package org.lineageos.aura.faceenroll;

import java.nio.ByteBuffer;

/** Packs Camera2 planes without rotating or mirroring, as the stock enrollment API does. */
final class Nv21 {
    private Nv21() {}

    static void pack(
            int width,
            int height,
            int left,
            int top,
            ByteBuffer[] planes,
            int[] rowStrides,
            int[] pixelStrides,
            byte[] output) {
        if (width <= 0
                || height <= 0
                || ((width | height | left | top) & 1) != 0
                || left < 0
                || top < 0
                || planes.length != 3
                || rowStrides.length != 3
                || pixelStrides.length != 3
                || output.length != width * height * 3 / 2) {
            throw new IllegalArgumentException("Invalid YUV420 dimensions");
        }
        for (int plane = 0; plane < 3; plane++) {
            int shift = plane == 0 ? 0 : 1;
            int w = width >> shift;
            int h = height >> shift;
            int step = plane == 0 ? 1 : 2;
            int offset = plane == 0 ? 0 : width * height + (plane == 1 ? 1 : 0);
            int rowStride = rowStrides[plane];
            int pixelStride = pixelStrides[plane];
            if (rowStride <= 0 || pixelStride <= 0) {
                throw new IllegalArgumentException("Invalid YUV420 strides");
            }
            ByteBuffer buffer = planes[plane].duplicate();
            int base =
                    buffer.position() + (top >> shift) * rowStride + (left >> shift) * pixelStride;
            for (int y = 0; y < h; y++) {
                int row = base + y * rowStride;
                for (int x = 0; x < w; x++) {
                    output[offset] = buffer.get(row + x * pixelStride);
                    offset += step;
                }
            }
        }
    }
}
