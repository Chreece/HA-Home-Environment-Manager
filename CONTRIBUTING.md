# Development and releases

## Branches

- `main` contains the latest working, validated integration.
- `dev` is the shared branch for development and testing.

Develop changes on `dev`. Open a pull request from `dev` to `main` when the
change is ready, review the resulting behavior, and merge only after validation
passes. Keep `dev` synchronized with `main` after promotion. Use these two
branches instead of creating separate feature or release branches.

## Validation

The **Validate Home Environment Manager** workflow runs on pushes and pull
requests to `main` and `dev`, and can be started manually. It checks Python and
JavaScript syntax, manifests and translations, the existing controller and
Home Assistant regressions, real browser interactions, and the installation
ZIP. The workflow has read-only repository permissions and does not publish
releases or change branches.

Keep regression tests in `.github/tests/` with the changes they protect.
Automated checks use simulated Home Assistant transport; any claim about a
physical appliance must be supported by evidence from that appliance.

## Releases

Set the intended beta version in `manifest.json` and add matching release
notes in `.github/releases/v<VERSION>.md`. This is the deliberate release
request. Validate on `dev`, then promote it to `main` after review.

The separate **Publish validated beta** workflow runs after a successful
validation push on `main`. It verifies the exact commit, creates a prerelease
and installation ZIP for a new version, and checks the tag, manifest and
uploaded and downloaded ZIP. Already published versions are never overwritten.
A changed `main` head or failed validation prevents publication.

Keep all releases and tags, including older prereleases. Publishing adds a new
release and leaves existing releases, their assets and all tags intact. Do not
delete or rewrite release history as part of publication or repository
maintenance. The validation workflow remains read-only; the publishing workflow
only adds newly versioned releases. An interrupted draft requires explicit
review before retrying.
