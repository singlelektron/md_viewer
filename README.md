# md_viewer

A planned Rust Markdown previewer for notes written in Neovim, with mathematical
notation as a primary concern.

**Status: repository initialization and technology evaluation only.** The owner
has requested a technology decision before application implementation. There is
no preview executable, Cargo package, Neovim plugin, or chosen rendering stack yet.

## Start here

- [Product scope](docs/PRODUCT.md): confirmed intent, open decisions, and proposed acceptance cases.
- [Technology options](docs/TECHNOLOGY_OPTIONS.md): browser, desktop WebView, and native GUI alternatives.
- [Owner guide](docs/OWNER_GUIDE.md): inspect and verify this planning repository.
- [Agent instructions](AGENTS.md): development and authorization boundaries.
- [Third-party notices](THIRD_PARTY_NOTICES.md): tooling references and incorporation status.

## Check the repository

Requires Git and Python 3.10 or newer; the documentation checker uses only the
Python standard library and needs no package installation.

```sh
python3 scripts/check_docs.py
git diff --check main...HEAD
```

These checks validate documentation hygiene and local file links, not a Markdown
previewer. Installation, application usage, Rust dependencies, and behavioral
tests will be added after the owner selects a route and authorizes implementation.

The GitHub Actions workflow runs the same documentation check on pull requests
and pushes to `main`. Its presence does not establish a hosted run or repository
protection. A project distribution license has not been selected.
