<p align="center">
  <img src="assets/logo.jpeg" alt="OldWin">
</p>

<br>

# OldWin

**OldWin** OldWin makes compatibility with Old Windows easier!
The crate relies heavily on [YY-Thunks](https://github.com/Chuyu-Team/YY-Thunks) and [VC-LTL5](https://github.com/Chuyu-Team/VC-LTL5) to solve the problem of missing APIs on older systems and API-SETs in the import table.

## Features

- **Effortless Integration**: Integrate YY-Thunks and VC-LTL5 just add entry to your `build-dependencies` and modify `build.rs`.
- **Backward Compatibility**: Effortlessly support Windows XP and later versions.
- **Binary Size Optimization**: Implement strategies to reduce the footprint of your application binaries.

## Usage

The minimum supported Rust version (MSRV) is **1.80**. This workspace pins
**1.99.1** in `rust-toolchain.toml` for development and verifies builds with it;
the Rust edition remains 2021.

Bundled native libraries:
- [YY-Thunks 1.2.3](https://github.com/Chuyu-Team/YY-Thunks/releases/tag/v1.2.3)
- [VC-LTL5 5.3.1](https://github.com/Chuyu-Team/VC-LTL5/releases/tag/v5.3.1)

The Windows-version features select native compatibility libraries; they do not
lower the minimum OS supported by Rust's standard library. In particular, the
`xp` and `vista` features do not make modern Rust `std` support those systems.

### 1. Add Dependency

Include OldWin in your `Cargo.toml` file:

> vc-ltl5 is dependent on yy-thunks, so if you use vc-ltl5 yy-thunks will be automatically added.

Upgrade `oldwin` and `oldwin-targets` together to **0.2**. The native packages
also use the 0.2 release line so Cargo cannot silently select the renamed
VC-LTL patch library for a 0.1 consumer.

```toml
# use yy-thunks and vc-ltl5 on Windows 7
[target.'cfg(target_family = "windows")'.dependencies]
oldwin-targets = { version = "0.2.0", default-features = false, features = [
  "win7",
  "yy-thunks",
  "vc-ltl5",
] }

[build-dependencies]
# use yy-thunks and vc-ltl5 on Windows 7
oldwin = { version = "0.2.0", default-features = false, features = [
  "win7",
  "yy-thunks",
  "vc-ltl5",
] }
```

### 2. Modify `build.rs`

```rust
// build.rs
fn main() {
    // These functions inspect Cargo's target, so this also works in cross-builds.
    oldwin::overwrite_subsystem(oldwin::Subsystem::Console);
    oldwin::inject();
}
```

### 3. Build the Windows 7 Standard Library

The `i686-win7-windows-msvc` and `x86_64-win7-windows-msvc` targets are
[Tier 3](https://doc.rust-lang.org/rustc/platform-support/win7-windows-msvc.html):
Rust does not distribute precompiled standard libraries for them. Do not use
`rustup target add` for these targets. Install a nightly toolchain with `rust-src`
and use `-Zbuild-std` instead:

```shell
rustup toolchain install nightly-2026-10-26 --profile minimal --component rust-src
```

Build on Windows with the MSVC C++ build tools and Windows SDK installed.
Cross-compilation additionally requires an MSVC-compatible linker and SDK libraries.

### 4. ***[Optional]*** Static Linking C Runtime

If you want to statically link the C runtime, you can modify your cargo configuration to add `-C target-feature=+crt-static` to the rustflags.

```toml
# config.toml
[target.x86_64-win7-windows-msvc]
rustflags = [
  "-C", "target-feature=+crt-static",
]

[target.i686-win7-windows-msvc]
rustflags = [
  "-C", "target-feature=+crt-static",
]
```

### 5. Build Your Project

Build your project using the {i686, x86_64}-win7-windows-msvc toolchain.

> `+nightly-2026-10-26` overrides the workspace's stable toolchain for `build-std`.
> For Windows 10 or newer, the ordinary `*-pc-windows-msvc` targets can use stable Rust.

```shell
cargo +nightly-2026-10-26 build --target i686-win7-windows-msvc -Zbuild-std
cargo +nightly-2026-10-26 build --target x86_64-win7-windows-msvc -Zbuild-std
```

### Library Consumers

YY-Thunks COFF `.obj` files are linked with `static:-bundle,+verbatim`, so Rust
does not try to unpack them as archives when building an `rlib`
([issue #1](https://github.com/honsunrise/oldwin/issues/1)). Keep `oldwin-targets`
as a normal dependency so the native search paths reach the final executable.
CRT archives also use `-bundle` and are linked on demand, rather than forced
wholesale into each consuming Rust library.
If you build a native `staticlib` rather than an `rlib`, `-bundle` does not embed
the thunk object: the final non-Rust link step must also supply the matching
YY-Thunks object and CRT libraries.

### Link Regression Smoke

`tests/link-smoke` exercises a Rust library calling a Windows API and a separate
executable consuming that library. Build and run it on Windows with:

```shell
cargo +nightly-2026-10-26 run --manifest-path tests/link-smoke/Cargo.toml --target x86_64-win7-windows-msvc -Zbuild-std
```

The default features are `win7,vc-ltl5`. Use `--no-default-features --features
win7,yy-thunks` for YY-Thunks alone, or change the OS feature and target
architecture. `RUSTFLAGS="-C target-feature=+crt-static"` selects the static CRT.
Compilation/linking success is not proof that a binary runs on XP or Vista.

### CI and Tests

GitHub Actions runs on pushes, pull requests, and manual dispatch:

- Linux workspace build/test on Rust **1.80.0** and **1.99.1**, plus Clippy and
  formatting checks.
- Native Windows MSVC build/run on both architectures and both stable versions,
  covering all five OS features with YY-Thunks alone, dynamic CRT, and static CRT.
- Windows-subsystem executables and nightly Windows 7 `build-std` on both architectures.
- PE checks for architecture, subsystem/version, thunk API imports, and CRT DLL imports.

The standalone consumer integration tests exercise the thunk clock against the
system clock, CRT reallocation across growth/shrink transitions, and CRT number
parsing with valid and invalid input. Run them on Windows:

```shell
cargo +1.99.1 test --manifest-path tests/link-smoke/Cargo.toml --target x86_64-pc-windows-msvc --locked --test runtime
```

For a Windows 7 standard-library build, use `+nightly-2026-10-26`,
`--target x86_64-win7-windows-msvc`, and `-Zbuild-std`. These tests are a separate
Cargo workspace; the root `cargo test --workspace` does not run them.

Inspect the built smoke executable separately:

```shell
python tests/verify-pe.py --exe tests/link-smoke/target/x86_64-pc-windows-msvc/debug/oldwin-link-smoke.exe --arch x86_64 --os win7 --crt dynamic --subsystem console
```

The PE check examines ordinary static imports, not delay imports or runtime DLL
loading. CI executes on modern Windows; it does not prove runtime compatibility
with Windows XP, Vista, or 7.

## Contributing

Contributions of all kinds are welcome, including:

- Issue reporting
- Pull Request submissions
- Documentation improvements

## License

OldWin is released under the [MIT License](LICENSE).

## Very Very Thanks

- [YY-Thunks](https://github.com/Chuyu-Team/YY-Thunks)
- [VC-LTL5](https://github.com/Chuyu-Team/VC-LTL5)
