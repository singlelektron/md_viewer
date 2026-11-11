# Local macOS validation

On 2026-11-11, at the owner's request, a local Apple Silicon smoke test found no
application failure in the cases below. This is limited platform evidence, not
full macOS acceptance or release validation.

## Initial smoke-test environment and revision

- macOS 26.6.2 (25G83), arm64, Xcode command-line tools.
- Rust/Cargo 1.96.0, Node.js 26.9.0, npm 11.19.1, Neovim 0.12.4.
- Initial application source: `1a084f8`; the first test pass only changed
  test/documentation files. The appearance follow-up below changes the application.
- Debug executable SHA-256:
  `ca6bb1bbc722aef2e3122d9a3572f04eca9573086b7854ad8f9739ffe3b35f29`.

## Automated local checks

- `npm ci --ignore-scripts --cache /private/tmp/md-viewer-npm-cache`: passed.
  An isolated writable cache avoided the execution sandbox's home-cache restriction.
- `npm run build`: passed; bundled offline frontend rebuilt before Rust build.
- `cargo build --locked`: passed for the native arm64 desktop executable.
  Cargo needed permission to populate its normal dependency cache.
- `cargo test --no-default-features --locked`: all 7 tests passed.
- `node frontend/app.test.cjs`: all 5 tests passed.
- `python3 tests/test_nvim_bridge.py`: passed after the fix below, including
  Insert-mode completion, unsaved updates, reload, buffer switching, stop/restart,
  child failures, and unchanged saved fixture bytes. This suite uses a fake viewer.
- `python3 scripts/check_docs.py` and committed diff whitespace check: passed.

The first bridge run failed at its filename assertion. macOS aliases `/var` to
`/private/var`; Neovim returned the resolved buffer path while Python passed the
unresolved temporary directory. Resolve that directory before passing it to
Neovim. This fixes a test assumption without changing application behavior.

## Native WebView checks

The GUI execution sandbox could not connect to macOS desktop services. The same
binary was launched outside that sandbox. Computer-use tooling requires an app
bundle, so an ignored, temporary `MD Viewer Test.app` wrapped a byte-identical
copy of the executable with a minimal Info.plist. No release bundle, installer,
signing, or system/editor configuration change was performed.

Observed through the application's native accessibility tree and screenshots:

| Case | Result |
| --- | --- |
| Open a disposable copy of `examples/notes.md` | Chinese, headings, code, tables, fractions, roots, and superscripts visibly rendered |
| Select Moonlit, Graphite, and Paper | All three themes switched and remained readable |
| Atomically replace the watched file | New document appeared |
| Temporarily move the watched file away | Error banner appeared while prior content remained |
| Restore valid text and correct an incomplete formula | Error cleared and the fraction rendered |
| Incomplete formula alongside ordinary content | Formula source fallback; surrounding content remained usable |
| HTML subscript, line break, and disclosure | Visible formatting and successful disclosure expansion |
| Script element and external link fixture | Script did not replace the page; clicking the link left the local preview unchanged |
| Clean Neovim launches the actual executable | Initial unsaved Chinese/formula content appeared with `Live · unsaved` |
| Change that buffer again without saving | New heading/formula appeared |
| Switch to a newly typed unnamed Markdown buffer | Window title and rendered document followed the new buffer |
| Check the saved fixture after unsaved edits | Exact original bytes `Saved original.\n` remained |
| Quit via Cmd-Q | Preview exited; disposable editor session was then closed |

Local evidence is retained under ignored `artifacts/macos/`: `graphite.png`,
`paper.png`, `invalid-math-html.png`, `recovered.png`, `unsaved-moonlit.png`, and
`switched-buffer.png`, alongside disposable fixtures. These artifacts are not
published in Git and are not required for normal builds.

## Appearance follow-up on 2026-11-11

The owner requested a real blur check and removal of the contrasting white title
bar, then asked for darker colors matching their current Mac Kitty configuration.
The delivered macOS appearance uses an overlay title bar with reserved native
button space, native HUD material, preset-dependent AppKit appearance, and the
[current platform palette](PRODUCT.md). The local `theme.conf`, `platform.conf`,
and private Kitty opacity override were read without modifying them. This is a
fixed palette in the viewer, not a runtime reader of personal configuration.

The only new WebView permissions are dragging and internal double-click zoom of
the main window. The theme select is outside the drag region. No dependency,
filesystem/shell capability, network access, or note-processing behavior was added.
Implementation uses the existing [Tauri window configuration](https://v2.tauri.app/reference/config/)
and its bundled native window effects.

Local checks passed again: frontend build, native Cargo build, Rust core tests,
frontend tests, Neovim bridge tests, formatting, documentation, committed diff
whitespace, and `cargo clippy --locked --all-targets -- -D warnings`.
The tested final executable SHA-256 is
`b094ca6a6dbbdbf1706da85c3c1ec7b296ad4f8f81afe67bd4bf7d3a95a92928`.
The temporary test bundle contains a byte-identical copy.

Native checks and evidence:

- The white title strip is absent; the toolbar and native buttons share the
  window's top edge. The filename is still available in the toolbar/window title.
- Moonlit, Graphite, and Paper switched successfully. Paper's header matches its
  content, and native appearance follows the preset.
- At approximately 373 logical pixels wide, the native-button space, filename,
  status, and theme menu remained usable, and prose wrapped within the window.
- Double-clicking the toolbar filename enlarged the window; repeating it restored
  the original size using the final permission set.
- A disposable AppKit backdrop drew large colored blocks and sharp stripes.
  Isolated-window captures did not include the desktop contribution: the initial
  red/blue captures were identical. They are not blur evidence.
- The owner moved the HUD-material preview over the backdrop on the actual
  desktop and explicitly confirmed visible blurred color blocks. This is human
  visual evidence for that material, not a pixel measurement or general acceptance.
- The owner found the experimental 0.35 tint too light. The delivered tint was
  changed to the same 0.88 opacity and palette as their Mac Kitty configuration;
  native material remains HUD. The darker final rendering was inspected, but no
  separate human sign-off or pixel-identical Kitty comparison is claimed.

Ignored local artifacts in `artifacts/macos-glass/` include the backdrop source,
test bundles, `before.png`, `kitty-moonlit.png`, `narrow-moonlit.png`,
`narrow-paper.png`, `final-moonlit.png`, and `final-graphite.png`.
Only disposable fixtures were edited. Test artifacts are not published in Git.

## Remaining limits

- No Intel Mac, other macOS versions, release build, signed/notarized installer,
  or distribution/upgrade testing.
- The blur observation is limited to the owner's desktop check described above.
  Isolated screenshots do not prove desktop blur, and final tint perception varies
  with the background and macOS appearance/accessibility settings.
- No network-disabled native run or network trace. Local bundled math rendered,
  but this run does not independently prove all offline/security guarantees.
- No full native overflow/punctuation edge-case sweep, actual popup-completion
  WebView observation, or long-running stress test. The headless bridge suite did
  exercise completion and lifecycle behavior separately.
- `tests/test_desktop.py` remains Linux-only; hosted CI remains Linux-only.
- Local agent-driven observations are separate from human acceptance, hosted CI,
  automated PR review, and merge authorization. See the associated PR for current
  hosted CI/review results. No merge or release is authorized by this record.

No dependencies or third-party materials were added. The existing project
distribution-license decision remains open.
