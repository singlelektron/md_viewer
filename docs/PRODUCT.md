# Product scope

## Confirmed intent

- Build a Rust Markdown preview application for notes edited in Neovim.
- Provide live preview, with mathematical formulas a central requirement.
- Initialize the repository and compare technology routes first.
- Wait for the owner's route decision before implementing the application.

This phase contains project documentation, Git setup, and documentation checks.
A successful repository check is not a working application baseline.

## Decisions still open

The [technology evaluation](TECHNOLOGY_OPTIONS.md) contains recommendations,
not approved architecture. In particular, the owner has not selected:

- An external browser, a desktop WebView window, or a native Rust GUI.
- Refresh after saving versus updates from unsaved Neovim buffers.
- KaTeX, MathJax, or another math renderer; required LaTeX commands and packages.
- Whether JavaScript rendering assets are acceptable within a Rust application.
- Supported operating systems; Linux is a working assumption for evaluation,
  not a committed platform support matrix.
- The Markdown dialect, math delimiters, macros, equation numbering/references,
  and any compatibility expectations for existing notes.
- Scroll following, multi-buffer behavior, exports, diagram support, and release scope.
- Project license, remote repository, visibility, and publication.

## Proposed first implementation scope

Subject to the owner's decision: one local Markdown document, readable headings,
lists, code blocks, links and local images, inline/display math, and live updates
that recover when a temporarily incomplete formula is corrected. Neovim remains
the editor; the previewer should not rewrite the note.

Suggested boundaries are offline rendering with bundled assets, no note upload
or telemetry, and explicit access only to the selected document and permitted
relative assets. Raw HTML and external-resource policies need to be specified
before implementation. These are proposals, not existing capabilities.

Cloud synchronization, a replacement editor, arbitrary LaTeX package execution,
and a full TeX distribution are outside the proposed first version.

## Proposed observable acceptance cases

Agree on representative notes and the supported syntax before turning these into
release criteria. No behavioral test below has run in this planning phase.

1. Preview a local Unicode note containing inline math, display math, fractions,
   sums, integrals, matrices, aligned equations, and the owner's common macros.
2. If unsaved updates are selected, edit in Insert mode without saving and see
   the current buffer; otherwise explicitly verify refresh after `:write`.
3. Temporarily leave braces or delimiters incomplete; show a local error or
   source fallback, keep the rest of the note usable, and recover after correction.
4. If numbering/references are selected, insert/delete earlier equations and
   verify that later numbers and references update without stale state.
5. Handle repeated saves, atomic file replacement, buffer switching, reconnects,
   and UTF-8 text without stale content overwriting newer updates.
6. If offline/private operation is selected, disconnect networking, render math
   and fonts, and verify that note bytes remain unchanged and no remote assets load.
7. If scroll following is selected, check it after formula/font layout settles,
   including edits above the viewport and manual scrolling in the preview.

Latency, memory use, and supported document size need measurements on agreed
fixtures and target hardware; no performance numbers are promised here.
