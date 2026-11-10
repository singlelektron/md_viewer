# Owner guide

## Build and use

Follow the [README](../README.md) for platform prerequisites and build commands.
Open `examples/notes.md` with `target/debug/md-viewer` to try saved-file mode.
Start with no file to see connection instructions; `--help` lists CLI options.

For actual typing-time preview, follow the [Neovim setup](../nvim/README.md), then
run `:MdViewerStart` in a Markdown buffer. This integration sends the buffer,
including unsaved content; the separate file mode only sees saved text. It never
saves the buffer automatically. Existing `MarkdownPreview` commands and shortcuts
are not replaced.

Use the window's theme selector for Moonlit, Graphite, or Paper. The choice is
session-only. To choose a startup theme from a terminal:

```sh
./target/debug/md-viewer --theme graphite examples/notes.md
```

Moonlit follows the inspected Kitty colors and 0.86 background opacity. Actual
appearance also depends on the compositor, WebView, and installed fonts. macOS
is a supported design target whose tests are deferred; it is not verified by
Linux screenshots or build results.

The note follows the window width. Very long unbroken formulas remain readable
through horizontal scrolling. Common HTML formatting works inside Markdown:

```markdown
Water: H<sub>2</sub>O<br>Another line with <mark>highlighted text</mark>.

<details>
<summary>Show explanation</summary>

An ordinary **Markdown paragraph** with $x^2 + y^2 = z^2$.

</details>

<p align="center">Centered text</p>
```

Keep the blank lines inside the disclosure when using Markdown or dollar math.
See the [supported HTML policy](PRODUCT.md) for the formatting and attribute
boundaries; inline styles and scripts are not supported.

## Verification

From the repository root:

```sh
npm ci --ignore-scripts
npm run build
cargo build --locked
cargo test --no-default-features --locked
node frontend/app.test.cjs
python3 tests/test_nvim_bridge.py
python3 scripts/check_docs.py
git diff --check main...HEAD
```

The Rust checks exercise document/protocol behavior without desktop dependencies.
Frontend tests cover browser-side update behavior. The Neovim test uses a clean
headless editor and fake child process to exercise actual buffer events, including
Insert-mode completion, switching, reloads, and child lifecycle. It verifies that
a saved fixture remains unchanged; it does not run the desktop renderer.

On Linux with an active desktop and `WebKitWebDriver` installed, run the native
integration check after building:

```sh
python3 tests/test_desktop.py
```

This opens disposable preview windows and a clean Neovim, sends unsaved text
through the Lua bridge and a test pipe relay into the real application, and
checks native KaTeX layout, width/punctuation regressions, safe HTML disclosure
interaction, themes, saved-file replacement, error recovery, and
unchanged note bytes. Reports and window screenshots go to ignored
`artifacts/desktop/`. No personal notes or editor settings are used. Inspect the
screenshots too: DOM presence alone does not prove visible formula glyphs.

For desktop acceptance, launch the built app and perform the cases in
[PRODUCT.md](PRODUCT.md): edit an unsaved formula, leave it incomplete and fix it,
switch notes, select each theme, check Linux translucency, and run without
networking. Record the actual result and revision in the handoff or PR. Do not
interpret documentation checks, a successful build, or mocked frontend tests as
a rendered desktop acceptance result. macOS testing is intentionally excluded
from this first verification round.

The documentation checker verifies required documents, final newlines, trailing
whitespace, and simple inline links to local files. It does not fetch external
URLs, validate anchors, or implement a complete Markdown parser.

## Troubleshooting

- **No window from Neovim:** check the configured executable path and `:messages`.
  Try that executable from a terminal, then use `:MdViewerStart` again.
- **Edits only appear after saving:** the viewer was opened in file mode; use the
  Neovim bridge for unsaved updates.
- **A formula shows source/error text:** finish its delimiters/braces or check the
  KaTeX-supported command set. Full LaTeX document/package support is outside scope.
- **A large note stops updating:** the 1 MiB note or 2 MiB encoded-message limit
  was reached. Shorten the note; the prior preview is retained until valid input
  arrives.
- **Themes/fonts differ:** Moonlit needs compositor transparency support; the UI
  uses locally installed fonts with fallbacks. Try Graphite for an opaque view.
- **Missing Linux WebView libraries:** install the Tauri prerequisites listed in
  the README for the actual distribution, then rebuild. Do not change compositor
  or global graphics settings merely because a build dependency is missing.

## Data, recovery, and publication

Notes remain in their existing files or unsaved Neovim buffers. There is no note
library, application-managed preferences file, or data migration. Renderer state
and theme choice are in memory; the system WebView may maintain its own engine
cache/runtime data. Closing the preview does not close or save the editor buffer.
Restart the viewer and resend/reopen the note to recover a preview; Neovim remains
responsible for saving and recovering unsaved editing work.

The app does not modify Kitty, Neovim, or desktop configuration. Remove the
opt-in runtime-path/setup entries from your own editor configuration to uninstall
its integration. No installer or global deployment is performed by a build.

Public GitHub synchronization is authorized for `singlelektron/md_viewer`.
Work belongs on task branches; `main` began as an empty bootstrap baseline.
Inspect the current PR/handoff for publication, hosted CI, and review results.
A local workflow file does not establish a hosted pass or branch protection.
Configured CI runs Linux build/lint, Rust core, frontend, and headless Neovim
checks; the native desktop check is local and macOS checks are excluded.
Merging, signing, and publishing release installers remain separate decisions.
