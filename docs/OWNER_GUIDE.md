# Owner guide

## What is available

This repository currently provides a project definition and a technology
comparison. It does not install or launch a previewer. Review
[PRODUCT.md](PRODUCT.md) and [TECHNOLOGY_OPTIONS.md](TECHNOLOGY_OPTIONS.md), then
select the display route, update behavior, and math compatibility needed for
your notes. Application development remains paused until that decision.

## Local verification

From the repository root, with Git and Python 3.10 or newer:

```sh
python3 scripts/check_docs.py
git diff --check main...HEAD
git status --short --branch
git log --oneline --decorate -5
git diff --stat main...HEAD
```

Expected results: the checker reports its file and link counts with no errors;
the diff check produces no output; the working tree is clean after handoff.
`main` is the initial empty baseline, and planning changes are on
`codex/bootstrap-planning`. These checks do not test application behavior.

The checker validates required documentation, final newlines, trailing
whitespace, and simple inline Markdown links to local files. It deliberately
does not fetch external URLs, validate anchors, or implement a full Markdown parser.

## CI and publishing

[Documentation CI](../.github/workflows/docs.yml) is configured for GitHub pull
requests and pushes to `main`. It has read-only repository permissions and does
not deploy. No remote, hosted CI result, or branch protection is established by
this local initialization. Remote creation/publication needs authorization for
the destination and visibility; merging needs authorization covering the merge.

## Data and recovery

There is no application data store, configuration, cache, or migration yet. This
phase does not read or modify personal notes or Neovim configuration. Planning
documents live in Git; inspect previous committed versions with `git show`.
Use a reviewed revert commit on a task branch to undo a committed change instead
of discarding unrelated working files. Local Git history is not an off-device
backup; keep a separate copy before destructive filesystem operations.

If a documentation check fails, fix the reported line or link and run it again.
If Git commands fail, verify that the command is running from the repository
root and that Git metadata is accessible; do not reinitialize or erase history
as a troubleshooting shortcut.
