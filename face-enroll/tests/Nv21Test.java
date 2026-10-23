// SPDX-License-Identifier: Apache-2.0
package org.lineageos.aura.faceenroll;

import java.nio.ByteBuffer;
import java.util.Arrays;

public final class Nv21Test {
    private static ByteBuffer plane(
            int width, int height, int rowStride, int pixelStride, int base, int value) {
        // Camera planes may omit trailing row padding, including the final interleaved byte.
        ByteBuffer b =
                ByteBuffer.allocate(
                        base + (height - 1) * rowStride + (width - 1) * pixelStride + 1);
        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                b.put(base + y * rowStride + x * pixelStride, (byte) (value + y * width + x));
            }
        }
        b.position(base);
        return b;
    }

    private static void check(byte[] expected, byte[] actual) {
        if (!Arrays.equals(expected, actual)) {
            throw new AssertionError(
                    "Expected " + Arrays.toString(expected) + ", got " + Arrays.toString(actual));
        }
    }

    public static void main(String[] args) {
        byte[] expected = {
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 40, 20, 41, 21, 42, 22, 43, 23
        };
        for (int pixelStride : new int[] {1, 2}) {
            ByteBuffer[] p = {
                plane(4, 4, 7, 1, 3, 0),
                plane(2, 2, 8, pixelStride, 2, 20),
                plane(2, 2, 8, pixelStride, 1, 40)
            };
            byte[] output = new byte[24];
            Nv21.pack(
                    4,
                    4,
                    0,
                    0,
                    p,
                    new int[] {7, 8, 8},
                    new int[] {1, pixelStride, pixelStride},
                    output);
            check(expected, output);
            if (p[0].position() != 3 || p[1].position() != 2 || p[2].position() != 1) {
                throw new AssertionError("Converter changed input position");
            }
        }
        ByteBuffer[] cropped = {
            plane(8, 6, 10, 1, 0, 0), plane(4, 3, 10, 2, 0, 60), plane(4, 3, 10, 2, 0, 80)
        };
        byte[] output = new byte[24];
        Nv21.pack(4, 4, 2, 2, cropped, new int[] {10, 10, 10}, new int[] {1, 2, 2}, output);
        check(
                new byte[] {
                    18, 19, 20, 21, 26, 27, 28, 29, 34, 35, 36, 37, 42, 43, 44, 45, 85, 65, 86, 66,
                    89, 69, 90, 70
                },
                output);
        try {
            Nv21.pack(4, 4, 1, 0, cropped, new int[] {10, 10, 10}, new int[] {1, 2, 2}, output);
            throw new AssertionError("Accepted misaligned crop");
        } catch (IllegalArgumentException expectedError) {
        }
        // A short plane must fail, rather than silently publishing an incomplete frame.
        try {
            Nv21.pack(
                    640,
                    480,
                    0,
                    0,
                    cropped,
                    new int[] {640, 320, 320},
                    new int[] {1, 1, 1},
                    new byte[460800]);
            throw new AssertionError("Accepted short plane");
        } catch (IndexOutOfBoundsException expectedError) {
        }
        System.out.println("NV21 planar/interleaved, padding, crop and bounds tests passed");
    }
}
