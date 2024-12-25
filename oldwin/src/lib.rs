use std::fmt::Display;

#[derive(Debug, Clone, Copy)]
pub enum Subsystem {
    Console,
    Windows,
}

impl Subsystem {
    pub fn as_str(&self) -> &str {
        match self {
            Self::Console => "CONSOLE",
            Self::Windows => "WINDOWS",
        }
    }
}

impl Display for Subsystem {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

pub fn overwrite_subsystem(subsystem: Subsystem) {
    let target_os = std::env::var("CARGO_CFG_TARGET_OS").unwrap();
    let target_env = std::env::var("CARGO_CFG_TARGET_ENV").unwrap();

    if target_os != "windows" && target_env != "msvc" {
        println!("cargo:warning=Please Only Use OldWin on Windows MSVC!");
        return;
    }

    let target_arch = std::env::var("CARGO_CFG_TARGET_ARCH").unwrap();
    let os_version = if target_arch == "x86_64" && cfg!(feature = "xp") {
        ",5.2"
    } else if target_arch == "x86" && cfg!(feature = "xp") {
        ",5.1"
    } else if cfg!(any(
        feature = "vista",
        feature = "win7",
        feature = "win8",
        feature = "win10"
    )) {
        ",6.0"
    } else {
        "" // use toolchain default
    };
    println!("cargo:rustc-link-arg-bins=/SUBSYSTEM:{subsystem}{os_version}");
    if matches!(subsystem, Subsystem::Windows) {
        println!("cargo:rustc-link-arg-bins=/ENTRY:mainCRTStartup");
    }
}

pub fn inject() {
    let target_os = std::env::var("CARGO_CFG_TARGET_OS").unwrap();
    let target_env = std::env::var("CARGO_CFG_TARGET_ENV").unwrap();
    let target_arch = std::env::var("CARGO_CFG_TARGET_ARCH").unwrap();
    let target_feature = std::env::var("CARGO_CFG_TARGET_FEATURE").unwrap();

    if target_os != "windows" || target_env != "msvc" {
        println!("cargo:warning=Please Only Use OldWin on Windows MSVC!");
        return;
    }

    let target_vendor = std::env::var("CARGO_CFG_TARGET_VENDOR").unwrap();
    match target_arch.as_str() {
        "x86" => {
            if cfg!(any(feature = "xp", feature = "vista", feature = "win7"))
                && target_vendor != "win7"
            {
                println!(
                    "cargo:warning=Use i686-win7-windows-msvc toolchain to build your project!"
                );
            }
        },
        "x86_64" => {
            if cfg!(any(feature = "xp", feature = "vista", feature = "win7"))
                && target_vendor != "win7"
            {
                println!(
                    "cargo:warning=Use x86_64-win7-windows-msvc toolchain to build your project!"
                );
            }
        },
        _ => {
            println!("cargo:warning=Unsupported Architecture!");
            return;
        },
    }

    if target_feature.contains("crt-static") {
        println!("cargo:rustc-link-arg=/NODEFAULTLIB:LIBVCRUNTIME");
        println!("cargo:rustc-link-arg=/NODEFAULTLIB:LIBUCRT");
        println!("cargo:rustc-link-lib=static:+whole-archive=libucrt");
        println!("cargo:rustc-link-lib=static=libvcruntime");
    } else {
        println!("cargo:rustc-link-arg=/NODEFAULTLIB:VCRUNTIME");
        println!("cargo:rustc-link-arg=/NODEFAULTLIB:UCRT");
        println!("cargo:rustc-link-lib=static:+whole-archive=ucrt");
        println!("cargo:rustc-link-lib=static=vcruntime");
    }

    #[cfg(feature = "xp")]
    println!("cargo:rustc-link-lib=static:+verbatim=YY_Thunks_for_WinXP.obj");

    #[cfg(feature = "vista")]
    println!("cargo:rustc-link-lib=static:+verbatim=YY_Thunks_for_Vista.obj");

    #[cfg(feature = "win7")]
    println!("cargo:rustc-link-lib=static:+verbatim=YY_Thunks_for_Win7.obj");

    #[cfg(feature = "win8")]
    {
        println!("cargo:rustc-link-lib=static:+verbatim=vccorlib140.pacth.lib");
        println!("cargo:rustc-link-lib=static:+verbatim=YY_Thunks_for_Win8.obj");
    }

    #[cfg(feature = "win10")]
    {
        println!("cargo:rustc-link-lib=static:+verbatim=vccorlib140.pacth.lib");
        println!("cargo:rustc-link-lib=static:+verbatim=YY_Thunks_for_Win10.0.10240.obj");
    }

    if cfg!(not(feature = "hidden-build-warning")) {
        #[cfg(feature = "xp")]
        {
            #[cfg(feature = "yy-thunks")]
            println!("cargo:warning=Using YY-Thunks for Windows XP");

            #[cfg(feature = "vc-ltl5")]
            println!("cargo:warning=Using VC-LTL5 for Windows XP");
        }

        #[cfg(feature = "vista")]
        {
            #[cfg(feature = "yy-thunks")]
            println!("cargo:warning=Using YY-Thunks for Windows Vista");

            #[cfg(feature = "vc-ltl5")]
            println!("cargo:warning=Using VC-LTL5 for Windows Vista");
        }

        #[cfg(feature = "win7")]
        {
            #[cfg(feature = "yy-thunks")]
            println!("cargo:warning=Using YY-Thunks for Windows 7");

            #[cfg(feature = "vc-ltl5")]
            println!("cargo:warning=Using VC-LTL5 for Windows 7");
        }

        #[cfg(feature = "win8")]
        {
            #[cfg(feature = "yy-thunks")]
            println!("cargo:warning=Using YY-Thunks for Windows 8");

            #[cfg(feature = "vc-ltl5")]
            println!("cargo:warning=Using VC-LTL5 for Windows 8");
        }

        #[cfg(feature = "win10")]
        {
            #[cfg(feature = "yy-thunks")]
            println!("cargo:warning=Using YY-Thunks for Windows 10");

            #[cfg(feature = "vc-ltl5")]
            println!("cargo:warning=Using VC-LTL5 for Windows 10");
        }
    }
}
