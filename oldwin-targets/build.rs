use mutually_exclusive_features::exactly_one_of;

fn main() {
    exactly_one_of!("xp", "vista", "win7", "win8", "win10");
}
