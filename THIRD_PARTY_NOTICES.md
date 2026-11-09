# Third-party materials

This project uses the libraries and assets below. Application implementations
were not copied from another project. The dependency sources and fonts are not
modified. Project governance follows the owner's supplied repo-bootstrap
instructions. **The owner has not selected a distribution license for this
application**; dependency licenses do not license the application itself.

## Application and build dependencies

| Material | Locked version | Upstream license | Use |
| --- | --- | --- | --- |
| [Tauri](https://github.com/tauri-apps/tauri) | 2.12.5 | Apache-2.0 OR MIT | Desktop window, WebView, local IPC |
| [tauri-build](https://github.com/tauri-apps/tauri) | 2.7.4 | Apache-2.0 OR MIT | Build-time assets and configuration |
| [pulldown-cmark](https://github.com/pulldown-cmark/pulldown-cmark) | 0.13.6 | MIT | Rust Markdown parsing |
| [ammonia](https://github.com/rust-ammonia/ammonia) | 4.2.4 | MIT OR Apache-2.0 | Rust HTML sanitization |
| [serde](https://github.com/serde-rs/serde) | 1.0.229 | MIT OR Apache-2.0 | Protocol data serialization |
| [serde_json](https://github.com/serde-rs/json) | 1.0.154 | MIT OR Apache-2.0 | JSON protocol |
| [KaTeX](https://github.com/KaTeX/KaTeX/tree/v0.19.1) | 0.19.1 | MIT for code/CSS; OFL-1.1 for fonts | Bundled offline math renderer |
| [commander](https://github.com/tj/commander.js) | 15.1.0 | MIT | KaTeX npm CLI dependency; not included in preview assets |

Exact direct and transitive declarations, target metadata, source archives, and
notice hashes are in [dependency-licenses.json](docs/dependency-licenses.json).
The inventory currently covers 319 distinct third-party Rust packages for Linux
x86-64 and macOS ARM64/x86-64, two npm packages, and 20 KaTeX TTF font files.
It records the default-feature resolved metadata graph, including build tools;
it does not assert that every listed crate is linked into the resulting binary.
Reading macOS metadata does not compile, run, or test macOS support.

## Preserved notices

- [Rust dependency notices](licenses/Rust-dependencies.txt) preserve supplied
  root-level license/notice files, grouping identical texts. For packages whose
  crate archives omit notices, [pinned upstream sources](licenses/upstream/sources.json)
  record the supplemental files and their provenance.
- [KaTeX code license](licenses/KaTeX-MIT.txt): copyright (c) 2013-2020 Khan
  Academy and other contributors; MIT.
- [KaTeX font notices and full license](licenses/KaTeX-fonts-OFL.txt): copyright
  (c) 2009-2010 Design Science, Inc.; (c) 2014-2018 Khan Academy; SIL OFL 1.1.
- [Commander license](licenses/Commander-MIT.txt): retained for the npm dependency.

KaTeX font licensing was checked in the downloaded TTF name tables, not inferred
from its package's MIT metadata. The font notice file retains each family's
original reserved-name declaration. The fonts are copied without changes; do
not relicense or rename them as original project work. Their full license is the
[official OFL 1.1](https://openfontlicense.org/documents/OFL.txt), also available
from [SIL's official repository](https://github.com/silnrsi/font-charis/blob/master/OFL.txt).
The standalone [license text](licenses/SIL-OFL-1.1.txt) contains no other font's
copyright or reserved names; the KaTeX notice file supplies the actual names.

The asset build copies these notices alongside the renderer. Retain the notices
with redistributed assets or binaries. UI font names reference installed system
fonts; no Kitty, JetBrains, or Nerd Font binaries are redistributed.

## Scope and limitations

All inventoried third-party packages have declared licenses. This is a source
and notice inventory, **not a complete legal audit**, a license-expression solver,
or an audit of every embedded source-file header. SPDX alternatives and `AND`
terms are preserved verbatim rather than collapsed to "MIT".

The graph includes MPL-2.0 components: cssparser 0.37.0 and 0.38.0,
cssparser-macros 0.7.1, dtoa-short 0.3.5, option-ext 0.2.0, and selectors 0.38.0.
Keep their MPL notices and corresponding source available when distributing
binaries; the inventory includes version-specific source archive links. Other
components have Unicode, BSD, ISC, Zlib, Apache, or combined terms; their supplied
texts are retained. No dependency source was changed by this project.

Upstream [objc2 licensing notes](licenses/upstream/objc2-d7d2fa23ceaa-LICENSE.txt)
discuss bindings derived from Apple SDKs and the need for the Xcode SDK terms.
Those SDK/distribution implications are not resolved by the crate SPDX metadata.
macOS SDK and release review remain deferred with macOS testing. Native system
libraries, platform SDKs, the Rust toolchain, and their licenses are outside this
Cargo/npm inventory; they are not vendored by this source repository. Reassess
them if building a self-contained distribution that includes those materials.

## Regeneration

Install the locked npm packages and fetch the locked Cargo graph for the recorded
targets, then run the standard-library-only generator from the repository root:

```sh
npm ci
cargo fetch --locked --target x86_64-unknown-linux-gnu
cargo fetch --locked --target aarch64-apple-darwin
cargo fetch --locked --target x86_64-apple-darwin
python3 scripts/license_inventory.py
python3 scripts/license_inventory.py --check
```

The generator uses `cargo metadata --locked --offline` and does not fetch network
resources. `--check` verifies generated records without writing them. Review
upstream notices and the pinned supplemental mapping when changing dependencies;
regeneration alone cannot establish license compatibility.

## CI dependency

**actions/checkout v7.0.1**, commit
`3d3c42e5aac5ba805825da76410c181273ba90b1`, is used remotely by CI; its source is
not vendored. Upstream license: MIT, copyright (c) 2018 GitHub, Inc. and
contributors. [Pinned source](https://github.com/actions/checkout/tree/3d3c42e5aac5ba805825da76410c181273ba90b1),
[license](https://github.com/actions/checkout/blob/3d3c42e5aac5ba805825da76410c181273ba90b1/LICENSE),
and [official tag](https://api.github.com/repos/actions/checkout/git/ref/tags/v7.0.1)
were checked on 2026-11-09. This source record does not establish a successful
hosted CI run or license any future copied action code.

**actions/setup-node v7.1.0**, commit
`949feb2413d6458794dcd2491c4babbbce0c15c1`, is used remotely by CI under MIT,
copyright (c) 2018 GitHub, Inc. and contributors. Its
[source and license](https://github.com/actions/setup-node/blob/949feb2413d6458794dcd2491c4babbbce0c15c1/LICENSE)
and [official tag](https://api.github.com/repos/actions/setup-node/git/ref/tags/v7.1.0)
were verified on 2026-11-09; no action code is copied into this repository.

CI installs Neovim v0.12.6 from its official release, verifying the published
SHA-256 digest, to run the editor integration test. Its
[upstream license](https://github.com/neovim/neovim/blob/v0.12.6/LICENSE.txt)
covers this test-tool use; the editor is not bundled with the application.
