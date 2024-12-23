#!/usr/bin/env bash

set -euxo pipefail

cargo publish -p oldwin-platform-vc-ltl5-x86-vista
cargo publish -p oldwin-platform-vc-ltl5-x86-win10
cargo publish -p oldwin-platform-vc-ltl5-x86-win7
cargo publish -p oldwin-platform-vc-ltl5-x86-win8
cargo publish -p oldwin-platform-vc-ltl5-x86-xp-part1
cargo publish -p oldwin-platform-vc-ltl5-x86-xp-part2

sleep 60

cargo publish -p oldwin-platform-vc-ltl5-x86_64-vista
cargo publish -p oldwin-platform-vc-ltl5-x86_64-win10
cargo publish -p oldwin-platform-vc-ltl5-x86_64-win7
cargo publish -p oldwin-platform-vc-ltl5-x86_64-win8
cargo publish -p oldwin-platform-vc-ltl5-x86_64-xp-part1
cargo publish -p oldwin-platform-vc-ltl5-x86_64-xp-part2
cargo publish -p oldwin-vc-ltl5

sleep 60

cargo publish -p oldwin-platform-yy-thunks-x86-vista
cargo publish -p oldwin-platform-yy-thunks-x86-win10
cargo publish -p oldwin-platform-yy-thunks-x86-win7
cargo publish -p oldwin-platform-yy-thunks-x86-win8
cargo publish -p oldwin-platform-yy-thunks-x86-xp

sleep 60

cargo publish -p oldwin-platform-yy-thunks-x86_64-vista
cargo publish -p oldwin-platform-yy-thunks-x86_64-win10
cargo publish -p oldwin-platform-yy-thunks-x86_64-win7
cargo publish -p oldwin-platform-yy-thunks-x86_64-win8
cargo publish -p oldwin-platform-yy-thunks-x86_64-xp
cargo publish -p oldwin-yy-thunks

sleep 60

cargo publish -p oldwin-targets
cargo publish -p oldwin
