use oldwin_targets as _;

#[cfg(not(windows))]
compile_error!("Build this regression fixture for a Windows MSVC target");

#[cfg(windows)]
pub fn precise_time() -> u64 {
    #[link(name = "kernel32")]
    unsafe extern "system" {
        fn GetSystemTimePreciseAsFileTime(time: *mut u64);
    }

    let mut time = 0;
    unsafe { GetSystemTimePreciseAsFileTime(&mut time) };
    time
}
