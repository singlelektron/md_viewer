#!/usr/bin/env python3
"""Record locked dependency declarations and preserve supplied notices, offline.

Run after fetching dependencies for the listed targets and `npm ci`. This is an
inventory, not an SPDX expression evaluator or a legal/compliance audit.
"""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
TARGETS = ("x86_64-unknown-linux-gnu", "aarch64-apple-darwin", "x86_64-apple-darwin")
NOTICE_PREFIXES = ("LICENSE", "LICENCE", "COPYING", "NOTICE", "UNLICENSE")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def font_notices(path):
    """Read TrueType name IDs 0/13/14 without an extra font-tool dependency."""
    data = path.read_bytes()
    count = struct.unpack_from(">H", data, 4)[0]
    result = {}
    for index in range(count):
        tag, _, offset, length = struct.unpack_from(">4sIII", data, 12 + 16 * index)
        if tag != b"name":
            continue
        table = data[offset:offset + length]
        _, records, base = struct.unpack_from(">HHH", table)
        for number in range(records):
            platform, _, _, name_id, size, pos = struct.unpack_from(
                ">HHHHHH", table, 6 + 12 * number
            )
            if name_id in (0, 13, 14):
                encoding = "utf-16-be" if platform in (0, 3) else "latin-1"
                result.setdefault(name_id, table[base + pos:base + pos + size].decode(encoding))
    return result


def collect():
    records = {}
    notice_texts = {}
    sources_path = ROOT / "licenses/upstream/sources.json"
    supplements = json.loads(sources_path.read_text()) if sources_path.exists() else {}

    def keep_notice(package, relative, data, source=None):
        text = "\n".join(line.rstrip() for line in data.decode("utf-8-sig").splitlines()) + "\n"
        key = digest(data)
        notice_texts.setdefault(key, {"text": text, "uses": []})["uses"].append(
            f"{package['name']} {package['version']}: {relative}"
        )
        item = {"file": relative, "sha256": key}
        if source:
            item["source"] = source
        package["notices"].append(item)

    for target in TARGETS:
        process = subprocess.run(
            ["cargo", "metadata", "--locked", "--offline", "--format-version", "1",
             "--filter-platform", target],
            cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE,
        )
        metadata = json.loads(process.stdout)
        for package in metadata["packages"]:
            if package["source"] is None:
                continue
            key = package["id"]
            if key in records:
                records[key]["targets"].append(target)
                continue
            record = {
                "name": package["name"], "version": package["version"],
                "license": package["license"], "source": package["source"],
                "source_archive": f"https://crates.io/api/v1/crates/{package['name']}/{package['version']}/download"
                if package["source"] == "registry+https://github.com/rust-lang/crates.io-index" else None,
                "repository": package["repository"], "targets": [target], "notices": [],
            }
            records[key] = record
            directory = Path(package["manifest_path"]).parent
            for path in sorted(directory.iterdir()):
                if path.is_file() and path.name.upper().startswith(NOTICE_PREFIXES):
                    keep_notice(record, path.name, path.read_bytes())
            for extra in supplements.get(f"{package['name']}@{package['version']}", []):
                keep_notice(record, extra["file"], (ROOT / "licenses/upstream" / extra["file"]).read_bytes(), extra["source"])

    rust = sorted(records.values(), key=lambda item: (item["name"], item["version"]))
    npm_lock = json.loads((ROOT / "package-lock.json").read_text())
    npm = []
    for relative, package in sorted(npm_lock["packages"].items()):
        if not relative:
            continue
        installed = json.loads((ROOT / relative / "package.json").read_text())
        if installed["version"] != package["version"]:
            raise ValueError(f"Installed {relative} does not match package-lock.json")
        npm.append({
            "name": installed["name"], "version": package["version"],
            "license": installed.get("license", package.get("license")),
            "source": package["resolved"], "integrity": package["integrity"],
            "role": "bundled renderer" if installed["name"] == "katex" else "npm CLI dependency; not bundled in the preview",
        })

    font_records = []
    notices = set()
    font_directory = ROOT / "node_modules/katex/dist/fonts"
    for path in sorted(font_directory.glob("*.ttf")):
        names = font_notices(path)
        notice = names.get(13, "")
        if "SIL Open Font License, Version 1.1" not in notice:
            raise ValueError(f"Unrecognized embedded font license: {path.name}")
        notices.add(notice)
        font_records.append({"file": path.name, "sha256": digest(path.read_bytes()),
                             "license": "OFL-1.1", "notice": notice})
    if not font_records:
        raise ValueError("No KaTeX TTF files found; install the locked npm dependencies first")

    inventory = {
        "schema_version": 1,
        "scope": "Locked Cargo dependency metadata for the listed targets with default features; metadata collection is not a platform build/test or a list of linked runtime code. npm lock and installed package metadata; bundled KaTeX TTF license records. Native system libraries and SDKs are excluded.",
        "cargo_lock_sha256": digest((ROOT / "Cargo.lock").read_bytes()),
        "npm_lock_sha256": digest((ROOT / "package-lock.json").read_bytes()),
        "targets": list(TARGETS), "rust": rust, "npm": npm,
        "katex_fonts": font_records,
        "missing_declared_licenses": [f"{p['name']}@{p['version']}" for p in rust + npm if not p["license"]],
        "without_supplied_notice_files": [f"{p['name']}@{p['version']}" for p in rust if not p["notices"]],
        "limitations": [
            "License expressions are recorded verbatim, including alternatives and conjunctions; no license compatibility solver was run.",
            "The package scan preserves root-level notice files and pinned supplemental upstream notices; it is not a full source-header audit.",
            "The upstream objc2 notice discusses Apple SDK-derived bindings; macOS SDK and distribution obligations remain unverified.",
            "The application has no selected distribution license; third-party licenses do not license the application itself.",
        ],
    }
    rust_text = ["Rust dependency notices\n\nGenerated by scripts/license_inventory.py.\n"
                 "Identical source notice files are grouped. Displayed line endings and trailing whitespace are normalized; hashes identify the original files.\n"
                 "License wording remains upstream text.\n"]
    for key, entry in sorted(notice_texts.items()):
        rust_text.append("\n" + "=" * 72 + "\n" + "\n".join(sorted(set(entry["uses"])))
                         + f"\nSHA-256: {key}\n\n" + entry["text"].rstrip() + "\n")
    font_text = "KaTeX fonts: original embedded license notices\n\n" + "\n\n".join(sorted(notices))
    font_text += "\n\nFull license text from https://openfontlicense.org/documents/OFL.txt\n\n"
    font_text += (ROOT / "licenses/SIL-OFL-1.1.txt").read_text()
    return {
        "docs/dependency-licenses.json": json.dumps(inventory, indent=2, ensure_ascii=False) + "\n",
        "licenses/Rust-dependencies.txt": "".join(rust_text),
        "licenses/KaTeX-fonts-OFL.txt": font_text,
        "licenses/KaTeX-MIT.txt": (ROOT / "node_modules/katex/LICENSE").read_text(),
        "licenses/Commander-MIT.txt": (ROOT / "node_modules/commander/LICENSE").read_text(),
    }, inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check generated outputs without writing")
    args = parser.parse_args()
    try:
        outputs, inventory = collect()
        different = []
        for relative, text in outputs.items():
            path = ROOT / relative
            if args.check:
                if not path.is_file() or path.read_text() != text:
                    different.append(relative)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
        if different:
            print("Stale license outputs: " + ", ".join(different), file=sys.stderr)
            return 1
        print(f"License inventory: {len(inventory['rust'])} Rust packages, {len(inventory['npm'])} npm packages, {len(inventory['katex_fonts'])} fonts.")
        print("Missing declarations:", inventory["missing_declared_licenses"])
        print("Without supplied notice files:", inventory["without_supplied_notice_files"])
        print("Metadata inventory only; not a legal audit or macOS test.")
        return int(bool(inventory["missing_declared_licenses"]))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"License inventory failed: {error}", file=sys.stderr)
        print("Fetch locked Cargo dependencies for the listed targets and run npm ci before regenerating.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
