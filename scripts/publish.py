#!/usr/bin/env python3
"""Validate a workspace release; upload only when --publish is explicitly supplied."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "oldwin-publish (https://github.com/honsunrise/oldwin)"


def release_request(event_name, ref, version, dry_run):
    """Bind a release request to its tag, or to main for a manual dry run."""
    if event_name == "push":
        if not ref.startswith("refs/tags/v"):
            raise ValueError("Automatic publishing requires a v-prefixed version tag")
        version = ref.removeprefix("refs/tags/v")
        source, upload = ref, True
    elif event_name == "workflow_dispatch":
        if ref != "refs/heads/main":
            raise ValueError("Run the manual release workflow from main")
        version = version.removeprefix("v")
        source = "HEAD" if dry_run else f"refs/tags/v{version}"
        upload = not dry_run
    else:
        raise ValueError(f"Unsupported release event: {event_name}")
    if not re.fullmatch(
        r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
        r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?",
        version,
    ):
        raise ValueError(f"Invalid release version: {version!r}")
    return source, version, upload


def workspace_packages(metadata, version):
    version = version.removeprefix("v")
    members = set(metadata["workspace_members"])
    packages = {
        p["name"]: p
        for p in metadata["packages"]
        if p["id"] in members and p.get("publish") != []
    }
    if not packages:
        raise ValueError("No publishable workspace packages")
    mismatched = [
        f"{name}={p['version']}"
        for name, p in packages.items()
        if p["version"].split("+")[0] != version
    ]
    if mismatched:
        raise ValueError(f"Requested version {version} does not match: {', '.join(mismatched)}")
    return packages


def internal_dependencies(package, packages):
    return {d["name"] for d in package["dependencies"] if d["name"] in packages}


def publish_order(packages):
    ordered, visiting, visited = [], set(), set()

    def visit(name):
        if name in visited:
            return
        if name in visiting:
            raise ValueError(f"Dependency cycle involving {name}")
        visiting.add(name)
        for dependency in sorted(internal_dependencies(packages[name], packages)):
            visit(dependency)
        visiting.remove(name)
        visited.add(name)
        ordered.append(name)

    # The build helper has no dependencies, but should be released after its native packages.
    for name in sorted(packages, key=lambda name: (name == "oldwin", name)):
        visit(name)
    return ordered


def pending_packages(packages, published):
    pending = []
    for name in publish_order(packages):
        existing = published[name]
        if existing is None:
            pending.append(name)
        elif existing["num"] != packages[name]["version"] or existing["yanked"]:
            raise ValueError(f"Cannot reuse published version of {name}: mismatched or yanked")
    return pending


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8")


def published_version(name, version):
    url = f"https://crates.io/api/v1/crates/{name}/{urllib.parse.quote(version, safe='')}"
    try:
        return json.loads(fetch(url))["version"]
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def require_indexed(name, version, index_text):
    for line in index_text.splitlines():
        entry = json.loads(line)
        if entry["vers"] == version and not entry["yanked"]:
            return
    raise ValueError(
        f"crates.io has not indexed {name} {version}; retry after registry indexing recovers"
    )


def check_dependency_index(name, version):
    lower = name.lower()
    if len(lower) < 3:
        index_path = f"{len(lower)}/{lower}"
    elif len(lower) == 3:
        index_path = f"3/{lower[0]}/{lower}"
    else:
        index_path = f"{lower[:2]}/{lower[2:4]}/{lower}"
    try:
        index_text = fetch(f"https://index.crates.io/{index_path}")
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        index_text = ""
    require_indexed(name, version, index_text)


def run(version, upload):
    metadata = json.loads(subprocess.check_output(
        ["cargo", "metadata", "--no-deps", "--locked", "--format-version=1"], cwd=ROOT
    ))
    packages = workspace_packages(metadata, version)
    if not upload:
        subprocess.run(
            ["cargo", "publish", "--workspace", "--dry-run", "--locked"], cwd=ROOT, check=True
        )
        print("Dry run completed; no crates were uploaded.", flush=True)
        return

    published = {name: published_version(name, p["version"]) for name, p in packages.items()}
    pending = pending_packages(packages, published)
    print(f"Already published: {len(packages) - len(pending)}; remaining: {len(pending)}", flush=True)
    for name in pending:
        for dependency in sorted(internal_dependencies(packages[name], packages)):
            check_dependency_index(dependency, packages[dependency]["version"])
        print(f"Publishing {name} {packages[name]['version']}", flush=True)
        subprocess.run(["cargo", "publish", "-p", name, "--locked"], cwd=ROOT, check=True)
    print("All requested package versions have been uploaded to crates.io.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="Expected release version, e.g. 0.2.1")
    parser.add_argument("--publish", action="store_true", help="Upload missing versions (default: dry run)")
    args = parser.parse_args()
    try:
        run(args.version, args.publish)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"Publish failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
