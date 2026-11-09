# Neovim integration

This small Lua module sends unsaved Markdown buffer snapshots to the desktop
viewer through its stdin pipe. It needs Neovim 0.11 or newer and the built
`md-viewer` executable. It does not start an HTTP server or write your notes.

Add the repository's `nvim` directory to your runtime path, then configure the
binary path in your own Neovim configuration:

```lua
vim.opt.runtimepath:append(vim.fn.expand("~/path/to/md_viewer/nvim"))
require("md_viewer").setup({
  command = { vim.fn.expand("~/path/to/md_viewer/target/debug/md-viewer") },
  debounce_ms = 60,
  theme = "moonlit",
})
```

Replace both example paths with your checkout location. If `md-viewer` is on the
PATH inherited by Neovim, `require("md_viewer").setup()` is enough. `command` is
an argument list, not a shell string; paths containing spaces do not need quotes
inside the Lua strings. The same setup works on Linux and macOS; macOS testing
is deferred in this version.

Open a Markdown buffer and use:

- `:MdViewerStart` to open the preview, including existing unsaved edits.
- `:MdViewerStop` to close the viewer process started by this module.
- `:MdViewerToggle` to toggle it.

An unnamed note works after `:setfiletype markdown`; no initial save is needed.
While the preview is running it follows entered Markdown buffers. Entering a
non-Markdown buffer leaves the last note selected. Buffer callbacks cover edits
without relying on `TextChangedI`, so completion-popup edits also trigger updates.
Reloads, undo/redo, renames, and the modified indicator refresh automatically.
The preview stops when Neovim exits. Closing the preview window allows a later
`:MdViewerStart` to launch it again.

Presets are `moonlit`, `graphite`, and `paper`. The setup theme applies when a new
viewer process starts; the window's selector changes the current session theme.
The default 60 ms debounce coalesces bursts of edits; it is not a measured
end-to-end latency guarantee. Notes larger than 1 MiB, or messages larger than
2 MiB including JSON encoding overhead, are rejected with a warning and retain
the last preview. Correcting the note resumes updates.

No existing `MarkdownPreview` command, keyboard mapping, installed plugin, or
global Neovim configuration is changed. Add your own mapping if desired:

```lua
vim.keymap.set("n", "<leader>mv", "<cmd>MdViewerToggle<cr>", { desc = "Markdown viewer" })
```

If startup fails, confirm that the executable exists and runs from a terminal,
then check `:messages`. A nonzero viewer exit includes a bounded stderr tail.
Use `:MdViewerStart` to reconnect after fixing the problem.

## Integration check

From the repository root:

```sh
python3 tests/test_nvim_bridge.py
```

The test launches a clean headless Neovim and a fake child transport. It checks
real buffer events, unsaved Unicode content, switching and reload, process
lifecycle, and saved-file preservation. It does not test the desktop renderer.
