{ pkgs, ... }:
{
  languages.rust = {
    enable = true;
    toolchainFile = ./rust-toolchain.toml;
  };

  packages = [
    pkgs.git
    pkgs.python3
    pkgs.actionlint
    pkgs.nixfmt
  ];

  # Use the machine's existing Nix cache configuration without adding trust settings.
  cachix.enable = false;

  scripts.oldwin-check.exec = ''
    set -euo pipefail
    cargo test --workspace --locked
    cargo clippy --workspace --all-targets --locked -- -D warnings
    python3 -m unittest discover -s tests -p 'test_publish.py' -v
    actionlint .github/workflows/ci.yml .github/workflows/publish.yml
  '';

  enterTest = ''
    oldwin-check
  '';
}
