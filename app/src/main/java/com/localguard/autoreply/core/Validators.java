package com.localguard.autoreply.core;

/** Checksum helpers used by the privacy guard. Pure Java, no Android imports. */
public final class Validators {
    private Validators() {}

    /** Luhn check used by payment cards. */
    public static boolean luhn(String digits) {
        int sum = 0;
        boolean dbl = false;
        for (int i = digits.length() - 1; i >= 0; i--) {
            int d = digits.charAt(i) - '0';
            if (d < 0 || d > 9) return false;
            if (dbl) {
                d *= 2;
                if (d > 9) d -= 9;
            }
            sum += d;
            dbl = !dbl;
        }
        return digits.length() > 0 && sum % 10 == 0;
    }

    private static final int[][] D = {
        {0,1,2,3,4,5,6,7,8,9},{1,2,3,4,0,6,7,8,9,5},{2,3,4,0,1,7,8,9,5,6},
        {3,4,0,1,2,8,9,5,6,7},{4,0,1,2,3,9,5,6,7,8},{5,9,8,7,6,0,4,3,2,1},
        {6,5,9,8,7,1,0,4,3,2},{7,6,5,9,8,2,1,0,4,3},{8,7,6,5,9,3,2,1,0,4},
        {9,8,7,6,5,4,3,2,1,0}};
    private static final int[][] P = {
        {0,1,2,3,4,5,6,7,8,9},{1,5,7,6,2,8,3,0,9,4},{5,8,0,3,7,9,6,1,4,2},
        {8,9,1,6,0,4,3,5,2,7},{9,4,5,3,1,2,6,8,7,0},{4,2,8,6,5,7,3,9,0,1},
        {2,7,9,3,8,0,6,4,1,5},{7,0,4,6,9,1,3,2,5,8}};
    private static final int[] INV = {0,4,3,2,1,5,6,7,8,9};

    /** Verhoeff check used by Aadhaar numbers (12 digits, last digit is the check digit). */
    public static boolean verhoeff(String digits) {
        int c = 0;
        int n = digits.length();
        for (int i = 0; i < n; i++) {
            int d = digits.charAt(n - 1 - i) - '0';
            if (d < 0 || d > 9) return false;
            c = D[c][P[i % 8][d]];
        }
        return n > 0 && c == 0;
    }

    /** Returns the Verhoeff check digit for a payload (used by tests to build valid Aadhaar-like numbers). */
    public static int verhoeffCheckDigit(String payload) {
        int c = 0;
        int n = payload.length();
        for (int i = 0; i < n; i++) {
            int d = payload.charAt(n - 1 - i) - '0';
            c = D[c][P[(i + 1) % 8][d]];
        }
        return INV[c];
    }
}
