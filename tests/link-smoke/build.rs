fn main() {
    let subsystem = if cfg!(feature = "gui") {
        oldwin::Subsystem::Windows
    } else {
        oldwin::Subsystem::Console
    };
    oldwin::overwrite_subsystem(subsystem);
    oldwin::inject();
}
