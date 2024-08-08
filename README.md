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

### 1. Add Dependency

Include OldWin in your `Cargo.toml` file:

> vc-ltl5 is dependent on yy-thunks, so if you use vc-ltl5 yy-thunks will be automatically added.

```toml
[dependencies]
# use yy-thunks and vc-ltl5 on Windows 7
oldwin = { version = "0.1.0", features = ["win7", "vc-ltl5"] }
```

### 2. Switch to {i686, x86_64}-win7-windows-msvc toolchain

Modify your project cargo configuration to use the {x86, x86_64}-win7-windows-msvc toolchain.

```shell
rustup component add rust-src
rustup target add i686-win7-windows-msvc
rustup target add x86_64-win7-windows-msvc
```

```toml
[unstable]
build-std = ["core", "alloc", "std", "proc_macro", "test"]
```

### 3. Build Your Project

Build your project using the {i686, x86_64}-win7-windows-msvc toolchain.

> Remember to use nightly toolchain.

```shell
cargo build --target i686-win7-windows-msvc -Zbuild-std
cargo build --target x86_64-win7-windows-msvc -Zbuild-std
```

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
