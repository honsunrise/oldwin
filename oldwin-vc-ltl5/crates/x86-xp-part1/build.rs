fn main() {
    let lib_dir = std::path::PathBuf::from(std::env::var_os("CARGO_MANIFEST_DIR").unwrap());
    println!(
        "cargo:rustc-link-search=native={}",
        lib_dir.join("lib").display()
    );
}
