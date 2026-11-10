# Product scope

## Selected direction

The owner has selected and authorized implementation of:

- A separate, minimal desktop preview window for Markdown written in Neovim.
- Rust for application logic, with HTML/CSS/JavaScript for presentation.
- Live updates while typing, including unsaved buffers.
- Ordinary inline mathematical formulas; advanced LaTeX compatibility is not a
  first-version requirement.
- Multiple visual presets, defaulting to a translucent dark background and light
  text matching the current Kitty/Neovim visual style.
- A Linux and macOS design target, with macOS testing explicitly deferred.
- Public synchronization to `singlelektron/md_viewer` on GitHub. Merge and release
  publication are separate actions and have not been authorized.

The selected implementation is Tauri, Rust Markdown parsing, KaTeX, and a small
Neovim Lua bridge over a child process's stdin. The earlier
[technology evaluation](TECHNOLOGY_OPTIONS.md) is historical, not an unresolved
architecture decision.

## First-version behavior

One preview process shows the selected Markdown buffer. Initial unsaved content,
subsequent edits, and changes of active Markdown buffer send complete snapshots.
A monotonically increasing revision prevents older input from replacing newer
content. The previewer never writes the source note. Standalone file mode is also
available and polls saved UTF-8 content; it cannot see an editor's unsaved buffer.

The Markdown surface includes headings, paragraphs, lists, code, blockquotes,
and ordinary math. KaTeX assets/fonts are bundled for offline runtime use.
Incomplete formulas produce local errors/source fallback while the rest of the
note remains available. No arbitrary TeX package execution is provided.

Content fills the available window width with modest padding. Inline formulas
stay on one line, and following sentence punctuation stays with the formula.
Normal prose uses strict punctuation line breaking. Oversized unbroken content
can be scrolled horizontally instead of being clipped or shrinking the text.

The three presets are Moonlit (default translucent dark), Graphite (opaque dark),
and Paper (light). The default uses Kitty's inspected background `#18131f` at
0.86 opacity and foreground `#f1e8f1`. Theme selection lasts for the current viewer
session. Installed system fonts are used for interface/text, with fallbacks;
matching font availability across operating systems is not guaranteed.

Moonlit also uses native background blur where supported. On Niri 26.04+ this
is an opt-in, application-specific compositor rule, matching the owner's Kitty
xray blur (blurred wallpaper). macOS is configured for the native
`underWindowBackground` material; its appearance and runtime remain untested.
Other Linux compositors require their own blur support/configuration. Opaque
themes cover the effect. CSS alone does not blur the desktop behind a WebView.

Input is limited to 1 MiB of note text and a 2 MiB encoded protocol frame.
Embedded HTML supports a sanitized formatting subset: paragraphs/headings,
`br`, emphasis, `sub`/`sup`, `kbd`, `mark`, `div`/`span`, lists, blockquotes,
code, tables, and `details`/`summary`. Table cell spans, ordered list numbering,
`details open`, and `align="left|center|right"` on paragraphs, divs, and table
cells are preserved. Standard CommonMark rules apply: use blank lines around
Markdown inside HTML blocks; dollar math inside a raw HTML block is literal.
Code spans/fences continue to display HTML literally. Scripts, event handlers,
arbitrary CSS/classes/IDs, embedded media, and forms are stripped. Images are
omitted and links have no navigation target, including native context menus.
There is no runtime server, note upload, or remote asset loading. Neovim setup is
opt-in; existing editor configuration, commands, and mappings remain untouched.

## Observable acceptance cases

1. Open a Unicode note containing `$x^2 + y^2 = z^2$`, a fraction, headings, and
   code. Verify readable text and correctly rendered inline formulas.
2. Type without saving, including while a completion popup is visible, and see
   the current text in the preview. Verify the disk file remains unchanged.
3. Leave a formula temporarily incomplete, then correct it. The surrounding
   document stays usable and the formula recovers.
4. Switch Markdown buffers during a burst of edits; the previous buffer's pending
   update must not replace the newly selected note. Stop/restart and reload must
   recover through a complete snapshot.
5. Switch each preset and inspect readable controls/content. The default window
   should show translucency on the actual Linux desktop, not just an RGBA CSS value.
6. Run without networking and verify math/fonts work. External content and raw
   HTML must not execute or navigate the privileged WebView.
7. In file mode, change or atomically replace a note and verify the preview updates.
8. Resize the preview: content uses the available width; inline formulas do not
   split and sentence punctuation does not wrap alone. Try HTML line breaks,
   subscripts, and a clickable disclosure block without enabling active content.

Tests and manual checks must be reported separately. Linux checks cannot establish
macOS behavior, and both platform support and transparency require real platform
validation before stronger claims. Debounce/poll intervals are implementation
settings, not measured end-to-end latency guarantees.

## Deferred scope

Complex LaTeX packages, equation-reference systems, image handling, exports,
editing inside the preview, multi-window sessions, cloud synchronization, and
cursor-synchronized scrolling are not first-version commitments. Ordinary preview
scroll position is preserved where practical; exact source-to-preview mapping is
not promised. macOS tests, signed installers, release packaging, and the project
license remain open.
