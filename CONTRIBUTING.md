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

**Every completed HEM change intended for `main` includes a new versioned release.**
For an explicitly approved stable milestone, use a SemVer version such as
`0.7.0` (not `0.7`). For development releases use the next unused beta.
Add matching notes in `.github/releases/v<VERSION>.md` before promotion. Treat a merge as complete
only after the `main` push validation and **Publish validated HEM release** workflows
succeed, and verify that the new prerelease tag and `environment_manager.zip`
asset are published. Stable releases must have `prerelease=false` and
the `make_latest=true` setting. If validation or publication fails, fix the problem and
publish the next safe version rather than reusing or overwriting an existing tag.
Validate on `dev`, then promote to `main` after review.

The separate **Publish validated HEM release** workflow runs after a successful
validation push on `main`. It verifies the exact commit, creates a prerelease
for beta versions or a full, latest release for stable versions, and verifies
the installation ZIP, tag, manifest, and uploaded/downloaded SHA256. Already published versions are never overwritten.
A changed `main` head or failed validation prevents publication.

Keep all releases and tags, including older prereleases. Publishing adds a new
release and leaves existing releases, their assets and all tags intact. Do not
delete or rewrite release history as part of publication or repository
maintenance. The validation workflow remains read-only; the publishing workflow
only adds newly versioned releases. An interrupted draft requires explicit
review before retrying.
