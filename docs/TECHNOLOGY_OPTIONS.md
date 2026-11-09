# Technology options

Status: **proposal for owner selection; no route is approved or implemented**.
Official sources checked on 2026-11-09. Relative effort assessments below are
engineering judgments, not measured performance or compatibility results.
See [PRODUCT.md](PRODUCT.md) for the actual requirements and open questions.

## Three separate choices

1. **Display:** external browser, desktop WebView, or native GUI.
2. **Updates:** saved file changes or unsaved Neovim buffer changes.
3. **Math:** KaTeX, MathJax, or an alternative with narrower verified coverage.

Rust can own the process, document state, Markdown parsing, and editor transport
while HTML/CSS/JavaScript handles display. That is a Rust application with a web
rendering layer, not an all-Rust dependency stack. Rust/WASM would still need a
browser or WebView and would not itself supply LaTeX typesetting.

## Display routes

| Route | Proposed composition | Advantages for this use | Main costs |
| --- | --- | --- | --- |
| A: external browser | Rust process + local HTTP + HTML/CSS + math engine | Smallest desktop integration scope; easy to place beside Neovim; mature math layout | Manage server lifetime, browser reconnect, local endpoint access, and scroll state; browser remains a separate application |
| B: Tauri desktop window | Rust core + Tauri 2 + system WebView + same web math engine | Dedicated preview window and desktop integration; can retain the same document/rendering design as A | Packaging and system dependencies; test each platform's WebView, not just one browser |
| C: native Rust GUI | egui or iced + explicit Markdown/math layout pipeline | Suitable when a native GUI without a WebView is a hard requirement | Formula typesetting, baseline layout, selection, accessibility, and Markdown behavior require additional integration |

**A is the lowest-scope starting point** if a browser window is acceptable.
Axum supports both [server-sent events](https://docs.rs/axum/latest/axum/response/sse/index.html)
and [WebSockets](https://docs.rs/axum/latest/axum/extract/ws/index.html). SSE is
sufficient for server-to-preview updates; bidirectional viewport/cursor messages
may justify WebSockets. The Neovim-to-Rust transport is a separate choice.

**B is a good fit when an independent application window matters.** Tauri accepts
static frontend assets; React/Vue and a large frontend framework are unnecessary.
Linux uses WebKitGTK, while other platforms use different system WebViews. The
Arch prerequisites include `webkit2gtk-4.1`. This adds a real target-system test
requirement, not evidence that Tauri is generally incompatible with Wayland.
See [frontend configuration](https://v2.tauri.app/start/frontend/),
[prerequisites](https://v2.tauri.app/start/prerequisites/),
[WebView versions](https://v2.tauri.app/reference/webview-versions/), and
[Linux graphics troubleshooting](https://v2.tauri.app/develop/debug/linux-graphics/).

**C is not the recommended first route for math-first Markdown.** Native GUI
frameworks do not automatically solve TeX layout. For example,
[egui_commonmark's math callback](https://docs.rs/egui_commonmark/latest/egui_commonmark/struct.CommonMarkViewer.html#method.render_math_fn)
expects the application to provide rendering; Iced's documented
[Markdown item enum](https://docs.rs/iced/latest/iced/widget/markdown/enum.Item.html)
has no dedicated math item. SVG/image rendering can be integrated, but then text
selection, sizing, caching, and accessibility need explicit solutions.

Keeping editor transport and document rendering separate could make A-to-B reuse
practical. Migration would still require window, IPC, asset-path, security, and
packaging work; it is not a promised zero-cost upgrade.

## Mathematical rendering

| Concern | KaTeX | MathJax 4 |
| --- | --- | --- |
| Common course-note math | Fractions, integrals, matrices, cases, align/aligned, and macros | Common TeX math, AMS environments, macros and extensions |
| Equation references | Supports explicit tags and some environment numbering; official table lists `\label`, `\ref`, and `\eqref` as unsupported | AMS automatic numbering and cross-equation references, including forward references |
| Live updates | Synchronous per-expression rendering; relatively direct application integration | Asynchronous typesetting and document state need coordinated updates |
| Incomplete expressions | `throwOnError: false` can show erroneous source | Error extensions such as `noerrors` can show source |
| Offline delivery | Bundle JS, CSS, and fonts | Bundle components, selected extensions, and font packages; configure local paths |
| Best fit | Common formulas and straightforward per-formula preview | Long mathematical notes using numbering/references and broader TeX features |

These claims come from the KaTeX [supported functions](https://katex.org/docs/supported.html),
[support table](https://katex.org/docs/support_table.html), and
[options](https://katex.org/docs/options.html), plus MathJax's
[AMS support](https://docs.mathjax.org/en/latest/input/tex/extensions/ams.html),
[numbering/references](https://docs.mathjax.org/en/v4.0/input/tex/eqnumbers.html),
[macros](https://docs.mathjax.org/en/latest/input/tex/extensions/newcommand.html),
and [typesetting API](https://docs.mathjax.org/en/latest/web/typeset.html).

Neither is a full LaTeX distribution or a promise of arbitrary packages, TikZ,
or complete `.tex` document compatibility. MathJax documents
[differences from TeX](https://docs.mathjax.org/en/latest/input/tex/differences.html).
Compare real notes against the exact supported command sets before committing.
There is no measured latency, binary-size, or memory comparison in this evaluation.

Important implementation consequences, once development is authorized:

- Treat incomplete input as normal while typing. Local errors or last-good-result
  fallback must not blank the whole preview; missing delimiters may also affect
  Markdown parsing before the formula engine sees an expression.
- MathJax dynamic previews need old-content cleanup, numbering reset when
  appropriate, isolated macro state, and handling of asynchronous completion.
  See its [dynamic editor guidance](https://docs.mathjax.org/en/v4.0/advanced/typeset.html).
- KaTeX macros also need document/session boundaries; avoid accidental leakage
  between notes. Numbering and macro changes can invalidate later formulas, so
  naive isolated block replacement is not always sufficient.
- Bundle assets and test disconnected operation. Copying only the MathJax entry
  script is insufficient when fonts/extensions load separately. See
  [KaTeX browser deployment](https://katex.org/docs/browser.html) and
  [MathJax hosting](https://docs.mathjax.org/en/latest/web/hosting.html).
- Renderer controls do not sanitize all Markdown HTML. Keep KaTeX's `trust`
  restricted, constrain macro expansion, and evaluate MathJax's safe extension
  alongside a separate raw-HTML policy. See [KaTeX security](https://katex.org/docs/security.html)
  and [MathJax safe options](https://docs.mathjax.org/en/latest/options/safe.html).

## If minimizing JavaScript is a requirement

**Rust math-core to MathML to browser/WebView** is an alternative worth a bounded
compatibility experiment. Its Rust API converts LaTeX to MathML Core. The project
documents incomplete command coverage and browser/font/CSS differences. It does
not provide an egui/iced native formula widget, and still needs a display/update
layer. See its [Rust API](https://docs.rs/math-core/latest/math_core/) and
[project notes](https://github.com/tmke8/math-core/blob/main/README.md).

**Typst to SVG/image** could serve a native GUI, but Typst's math syntax differs
from LaTeX. Preserving existing LaTeX-in-Markdown notes would require a conversion
layer with its own compatibility scope. It is more attractive if adopting Typst
syntax is intentional. See [Typst math](https://typst.app/docs/reference/math/)
and its [LaTeX migration guide](https://typst.app/docs/guides/for-latex-users/).

Neither alternative should be treated as drop-in KaTeX/MathJax compatibility.

## What live preview means in Neovim

| Mode | Mechanism | What the owner sees |
| --- | --- | --- |
| Refresh after save | Rust file watcher, e.g. notify | Saved content updates; unsaved typing is invisible |
| Preview while typing | Neovim buffer events via a small Lua bridge or Msgpack-RPC client | Unsaved text updates, including Insert-mode edits |

For the typing workflow, prefer `nvim_buf_attach` events with revision tracking,
a short coalescing/debounce interval, and a full snapshot on connect/reconnect.
Use `changedtick` with buffer/session identity to reject stale updates; handle
detach/reload and apply RPC batches correctly. This is a proposed design, not a
completed plugin. [Neovim buffer updates](https://neovim.io/doc/user/api/#api-buffer-updates)
document both RPC and Lua paths. Autocmd alternatives require care:
[`TextChangedI`](https://neovim.io/doc/user/autocmd/#TextChangedI) excludes edits
while the completion popup is visible, for which `TextChangedP` is relevant.

For save-only mode, watch replacement/rename/create events as well as writes;
watching the parent directory and resynchronizing is a practical design option.
Editors can replace files on save, and network filesystems can behave differently,
as described in [notify's known problems](https://docs.rs/notify/latest/notify/#known-problems).
Do not allow a save event to overwrite a newer unsaved-buffer preview.

## Rust Markdown parsing and preview quality

Both candidates below expose math source; neither typesets TeX itself.

- **pulldown-cmark:** event-based parsing, `ENABLE_MATH`, and source byte ranges
  through `into_offset_iter`. Suitable for a relatively direct rendering pipeline.
  See [math support](https://docs.rs/pulldown-cmark/latest/pulldown_cmark/struct.Options.html#associatedconstant.ENABLE_MATH)
  and [offset iteration](https://docs.rs/pulldown-cmark/latest/pulldown_cmark/struct.Parser.html#method.into_offset_iter).
- **Comrak:** AST/source positions and math extensions for dollar syntax,
  `\(...\)` / `\[...\]`, and code-style math. Useful for richer block processing.
  See [extension options](https://docs.rs/comrak/latest/comrak/options/struct.Extension.html)
  and [source positions](https://docs.rs/comrak/latest/comrak/nodes/struct.Sourcepos.html).

Use parsed math nodes rather than a global dollar-sign substitution: code spans,
code fences, escaped dollars, and currency text need correct treatment. The chosen
dialect and delimiter policy need fixtures from actual notes.

Source positions help map editor lines to rendered blocks, but do not implement
scroll following by themselves. Formula/font loading changes heights. Start by
preserving a visible block/anchor and decide separately whether cursor following
and reverse synchronization are required. Debouncing, revision ordering, macro
state, and measured document size should inform incremental rendering decisions.

For a local web service, propose loopback binding, session-scoped access and origin
checks, limited asset roots, and protection against path traversal. For Tauri,
expose only necessary commands/capabilities. Include the intended privacy and
resource behavior in the selected implementation scope; no endpoint exists yet.

## Suggested selection

- **Choose A** to minimize initial integration and use a browser beside Neovim.
- **Choose B** if a dedicated desktop preview window is part of the desired experience.
- **Choose C** only if avoiding a WebView outweighs the extra math integration scope.

For either A or B, choose **MathJax 4** when equation numbering, references, and
broader TeX features are central; choose **KaTeX** for common course-note formulas
with simpler update handling. Given the stated math priority, A + MathJax is a
reasonable provisional recommendation, subject to the owner's actual note syntax
and window preference. Unsaved buffer updates are the recommended interpretation
of typing-time preview, but the owner should choose that behavior explicitly.

No Cargo manifest, frontend package, plugin, dependency installation, or runtime
experiment was created to make this comparison. Source documentation is evidence
of available APIs, not proof that this application works on the owner's machine.
