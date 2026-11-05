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

Set the intended version in `manifest.json` and add matching release notes in
`.github/releases/v<VERSION>.md`. Validate the exact commit, promote it to
`main`, and publish its tag and installation ZIP from that tested commit.
Mark beta versions as prereleases. Verify that the published tag, manifest
version and ZIP match before removing a superseded GitHub Release.

Repository cleanup keeps the newest published release and the `main` and `dev`
branches. The validation workflow never performs this cleanup automatically.
