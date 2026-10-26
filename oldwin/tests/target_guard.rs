use std::process::Command;

#[test]
fn build_script_target_guards() {
    // Re-execute this test so Cargo target variables stay isolated from other tests.
    if std::env::var_os("OLDWIN_TARGET_GUARD_CHILD").is_some() {
        oldwin::overwrite_subsystem(oldwin::Subsystem::Console);
        oldwin::inject();
        return;
    }

    for (os, environment, features, supported) in [
        ("linux", "gnu", None, false),
        ("none", "", None, false),
        ("windows", "gnu", None, false),
        ("windows", "msvc", Some(""), true),
    ] {
        let mut child = Command::new(std::env::current_exe().unwrap());
        child
            .args(["--exact", "build_script_target_guards", "--nocapture"])
            .env("OLDWIN_TARGET_GUARD_CHILD", "1")
            .env("CARGO_CFG_TARGET_OS", os)
            .env("CARGO_CFG_TARGET_ENV", environment)
            .env("CARGO_CFG_TARGET_ARCH", "x86_64")
            .env("CARGO_CFG_TARGET_VENDOR", "pc");
        if let Some(features) = features {
            child.env("CARGO_CFG_TARGET_FEATURE", features);
        } else {
            child.env_remove("CARGO_CFG_TARGET_FEATURE");
        }
        let output = child.output().unwrap();
        assert!(
            output.status.success(),
            "{os}/{environment}: {}",
            String::from_utf8_lossy(&output.stderr)
        );
        let stdout = String::from_utf8(output.stdout).unwrap();
        if supported {
            assert!(stdout.contains("cargo:rustc-link-arg-bins=/SUBSYSTEM:CONSOLE"));
        } else {
            assert!(!stdout.contains("cargo:rustc-link-"), "{stdout}");
        }
    }
}
