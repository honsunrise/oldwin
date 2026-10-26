use std::ffi::{c_char, c_void};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

// Resolve against the CRT selected by Rust and OldWin, including +crt-static.
unsafe extern "C" {
    fn malloc(size: usize) -> *mut c_void;
    fn realloc(ptr: *mut c_void, size: usize) -> *mut c_void;
    fn free(ptr: *mut c_void);
    fn strtod(text: *const c_char, end: *mut *mut c_char) -> f64;
}

#[test]
fn precise_time_matches_the_system_clock() {
    let before = SystemTime::now();
    let ticks = oldwin_link_smoke::precise_time();
    let after = SystemTime::now();
    // FILETIME counts 100 ns intervals since 1601; Unix time starts in 1970.
    let unix_ticks = ticks.checked_sub(116_444_736_000_000_000).unwrap();
    let actual = UNIX_EPOCH
        + Duration::new(
            unix_ticks / 10_000_000,
            (unix_ticks % 10_000_000) as u32 * 100,
        );
    // The fallback on old Windows can use the coarser 15.625 ms system clock.
    let tolerance = Duration::from_millis(20);
    assert!(actual >= before - tolerance && actual <= after + tolerance);
}

#[test]
fn crt_reallocation_preserves_bytes_when_growing_and_shrinking() {
    let original = *b"oldwin-crt-check";
    unsafe {
        let ptr = malloc(original.len()).cast::<u8>();
        assert!(!ptr.is_null());
        ptr.copy_from_nonoverlapping(original.as_ptr(), original.len());

        let grown = realloc(ptr.cast(), 64).cast::<u8>();
        assert!(!grown.is_null());
        let mut after_growth = [0; 16];
        after_growth
            .as_mut_ptr()
            .copy_from_nonoverlapping(grown, original.len());

        let shrunk = realloc(grown.cast(), 8).cast::<u8>();
        assert!(!shrunk.is_null());
        let mut after_shrink = [0; 8];
        after_shrink
            .as_mut_ptr()
            .copy_from_nonoverlapping(shrunk, 8);
        free(shrunk.cast());

        assert_eq!(after_growth, original);
        assert_eq!(after_shrink, original[..8]);
    }
}

#[test]
fn crt_number_parsing_reports_the_unconsumed_input() {
    unsafe {
        let valid = b"-12.5 trailing\0";
        let mut end = std::ptr::null_mut();
        assert_eq!(strtod(valid.as_ptr().cast(), &mut end), -12.5);
        assert_eq!(end.cast_const(), valid.as_ptr().add(5).cast::<c_char>());

        let invalid = b"not-a-number\0";
        assert_eq!(strtod(invalid.as_ptr().cast(), &mut end), 0.0);
        assert_eq!(end.cast_const(), invalid.as_ptr().cast::<c_char>());
    }
}
