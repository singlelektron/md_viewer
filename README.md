# md_viewer

A quiet desktop Markdown preview for Neovim. Rust handles document state, input,
and Markdown parsing; a Tauri window presents static HTML/CSS and bundled KaTeX.
The interface stays small: note title, connection status, and a theme selector.

The default **Moonlit** theme follows the owner's Kitty palette: translucent
`#18131f` at 86% opacity, `#f1e8f1` text, and a muted rose accent. **Graphite** is
an opaque dark alternative; **Paper** is a light alternative. Theme selection is
per session. No terminal or editor settings are modified.
Moonlit supports a frosted background through native macOS material or an
[opt-in Niri blur rule](docs/OWNER_GUIDE.md); desktop blur needs compositor support.

Linux has automated CI coverage. A local Apple Silicon macOS build and native
WebView smoke test passed; see the [macOS validation record](docs/MACOS_VALIDATION.md)
for the tested environment, evidence, and remaining coverage limits.

## Build and open

Requires Rust 1.90+, Node.js 22.12+, and the platform's Tauri prerequisites.
Linux needs GTK 3 and WebKitGTK 4.1 development libraries; macOS needs Xcode
command-line development tools. See the official
[Tauri prerequisites](https://v2.tauri.app/start/prerequisites/) for your platform.

From the checkout root:

```sh
npm ci --ignore-scripts
npm run build
cargo build --locked
./target/debug/md-viewer examples/notes.md
```

This file mode refreshes saved changes. For an optimized local executable, use
`cargo build --release --locked` and `target/release/md-viewer`. A separate Tauri
CLI, frontend development server, or Node.js process is not needed at runtime.

## Preview while typing

Use the [Neovim integration](nvim/README.md) to connect unsaved buffers. After
adding its runtime path and configuring the executable, run `:MdViewerStart` in
a Markdown buffer. `:MdViewerStop` closes it; `:MdViewerToggle` toggles it. New
unnamed notes work after `:setfiletype markdown`, without an initial save.

Inline formulas such as `$x^2 + y^2 = z^2$` render locally. The first version
focuses on ordinary formulas, not arbitrary LaTeX packages or equation-reference
systems. Content follows the window width, with unbroken inline formulas and
attached sentence punctuation. A [safe HTML subset](docs/PRODUCT.md) supports
line breaks, subscripts/superscripts, highlights, tables, and disclosure blocks.
Images are omitted and links are inert. There is no note upload, runtime asset
download, or local HTTP server.

## Development and scope

- [Product scope](docs/PRODUCT.md): selected requirements and acceptance cases.
- [Owner guide](docs/OWNER_GUIDE.md): checks, troubleshooting, and data behavior.
- [Agent instructions](AGENTS.md): development and authorization boundaries.
- [Third-party notices](THIRD_PARTY_NOTICES.md): dependency and asset records.
- [Earlier technology comparison](docs/TECHNOLOGY_OPTIONS.md): historical alternatives; the product scope is authoritative.

```sh
cargo test --no-default-features --locked
node frontend/app.test.cjs
python3 tests/test_nvim_bridge.py
python3 scripts/check_docs.py
```

These cover different layers and do not replace a real desktop acceptance check.
See the owner guide for that path. The repository is intended for public GitHub
synchronization; the handoff/PR records actual hosted CI and publication status.
A project distribution license has not yet been selected.
