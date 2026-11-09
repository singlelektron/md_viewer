# Agent instructions

## Sources and scope

Read [docs/PRODUCT.md](docs/PRODUCT.md) for approved intent and open decisions,
[README.md](README.md) for project entry points, and
[docs/OWNER_GUIDE.md](docs/OWNER_GUIDE.md) for operation and verification.
[docs/TECHNOLOGY_OPTIONS.md](docs/TECHNOLOGY_OPTIONS.md) records proposals only.
Keep one authoritative home for each requirement and link to it elsewhere.

The owner requested repository initialization and analysis before implementation.
Do not create a Cargo package, application, renderer, or Neovim integration until
the owner chooses a route and authorizes development. Document proposed choices
as proposals; do not present them as accepted requirements or implemented behavior.
English is the default for repository documents and technical instructions;
respond to the owner in their conversational language.

## Authority and Git

Routine reversible work, local branches/commits, proportionate checks, and
in-scope fixes may proceed under the current task's authorization. Preserve all
unrelated files, staged/unstaged edits, untracked work, and history. Stage only
task files. Do not discard, stash, or commit unrelated work.

Keep `main` stable and use task branches such as `codex/<topic>`. The initial
empty root commit is the bootstrap base; subsequent changes belong on branches.
Deliver a commit and a reviewable PR when publication is authorized, otherwise
a local diff and PR-style handoff. Remote creation/pushes, visibility/access or
protection changes, publication, deployment, and merging require authorization
covering those actions. PR authorization includes its branch push, not merging.
Honor authorization already given without repeatedly asking for it.

Ask for missing owner decisions when changing material product scope, governance,
authorization boundaries, security/privacy/data guarantees, significant costs,
or when an action is destructive or hard to reverse. Ordinary choices inside
an approved implementation do not need an approval ceremony.

## Third-party code and attribution

- Research open-source implementations, algorithms, and architecture freely.
- Prefer maintained libraries over copying implementation code when appropriate.
- Before adding dependencies, code, assets, fonts, datasets, or binaries, establish
  a license or other valid legal basis compatible with the intended use.
- Preserve required copyright, license, and attribution notices. Record incorporated
  materials, sources, and licensing in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
  or an equivalent dependency notice record.
- Keep materials with unknown or incompatible rights out of the project. Relying
  on rights-holder permission or a legal exception requires explicit human approval
  and a documented basis; project-owner approval alone cannot grant outside rights.
- Independently implemented general ideas need no formal attribution; substantial
  technical influences may be acknowledged voluntarily.
- Disclose added third-party code/assets/dependencies and unresolved licensing
  questions at PR or local handoff. Never claim a license audit that did not occur.

## Verification and handoff

Current commands, from the repository root:

```sh
python3 scripts/check_docs.py
git diff --check main...HEAD
```

For another PR base, use its actual base instead of `main`. A clean uncommitted
diff does not validate committed changes. Add build/run and behavior checks only
when implementation exists. Validate affected outcomes and failures in proportion
to risk; use disposable fixtures for data/recovery checks and never real notes
for destructive experiments. High-consequence releases need suitable human review.

Use [.github/pull_request_template.md](.github/pull_request_template.md) for PRs
or local handoffs. Report local checks, hosted CI, AI review, human acceptance,
merge, and deployment separately. Do not claim a working product from structural
checks. Update commands and instructions when the project becomes runnable.

When work and relevant checks are complete, use a normal review-ready PR; drafts
are for incomplete work or requested early review. Let configured CI and available
automated review run, including Codex Code Review when configured. Fix confirmed
correctness, security, and data issues; explain declined suggestions. Substantive
changes require affected checks and renewed review when earlier evidence no longer
applies. Do not mandate an extra reviewer or loop indefinitely. AI feedback is not
formal human approval or merge authorization. Required CI must pass before merge;
unavailable hosted checks need an explicit owner decision. Respect protections.
