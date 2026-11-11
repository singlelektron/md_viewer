# Local macOS validation

On 2026-11-11, at the owner's request, a local Apple Silicon smoke test found no
application failure in the cases below. This is limited platform evidence, not
full macOS acceptance or release validation.

## Environment and revision

- macOS 26.6.2 (25G83), arm64, Xcode command-line tools.
- Rust/Cargo 1.96.0, Node.js 26.9.0, npm 11.19.1, Neovim 0.12.4.
- Application source: `1a084f8`; this task changes only test/documentation files.
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

## Remaining limits

- No Intel Mac, other macOS versions, release build, signed/notarized installer,
  or distribution/upgrade testing.
- Moonlit rendered, but screenshots alone do not establish the native material's
  desktop translucency/blur; detailed-background compositor acceptance remains open.
- No network-disabled native run or network trace. Local bundled math rendered,
  but this run does not independently prove all offline/security guarantees.
- No native resize/overflow/punctuation edge-case sweep, actual popup-completion
  WebView observation, or long-running stress test. The headless bridge suite did
  exercise completion and lifecycle behavior separately.
- `tests/test_desktop.py` remains Linux-only; hosted CI remains Linux-only.
- Local agent-driven observations are separate from human acceptance, hosted CI,
  automated PR review, and merge authorization. See the associated PR for current
  hosted CI/review results. No merge or release is authorized by this record.

No dependencies or third-party materials were added. The existing project
distribution-license decision remains open.
