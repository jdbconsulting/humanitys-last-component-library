# Website versions and releases

Development happens on `dev`. `main` holds reviewed release commits. The website
deploys to production only when a stable `vX.Y.Z` tag is pushed (or an existing
release tag is manually redeployed). Pushing `dev`, merging a pull request, or
running a local production build does not deploy the website.

The first versioned development cycle is **0.2.0-dev**, with **0.2.0 unreleased**
until promotion. The original website
is recorded retrospectively as **0.1.0**; its release date is not known. Adding
that history entry does not create a historical Git tag or GitHub Release.

## Sources of truth

- [`package.json`](../package.json): website build version. Use `X.Y.Z-dev` during
  development and `X.Y.Z` for a prepared release. Update it with `npm version
<version> --no-git-tag-version` so both root versions in `package-lock.json`
  stay synchronized without creating a commit or tag.
- [`src/lib/release-history.json`](../src/lib/release-history.json): newest-first
  release notes shown at `/docs/#revision-history` and used as GitHub release
  notes. Each entry has a stable version, `unreleased` or `released` status, a
  `releasedOn` date (`YYYY-MM-DD`, or `null` while unreleased), and a changes list.
- [`src/lib/website-version.ts`](../src/lib/website-version.ts): imports the npm
  version for the footer on every page, including prerendered HTML.

The website version describes the site and the generator bundled with it. The
configuration `schema_version` has its own compatibility rules and is not bumped
just because the website version changes.

`npm run release:check` checks versions, history order, status, and dates.
`npm run build` runs this check automatically before generating the static site.
`npm run release:check -- --stable` rejects development versions, and
`npm run release:check -- --tag v0.2.0` additionally requires an exact tag match.
These commands validate metadata; they do not commit, tag, publish, or deploy.

## Commit development work

Keep feature work and fixes on `dev` (or merge feature branches into `dev`). For
the current cycle, keep `package.json` at `0.2.0-dev` and the 0.2.0 history entry
unreleased with a null date. Add user-visible changes to that entry as work lands.

Before committing:

```sh
git switch dev
git status --short
npm run release:check
npm run test:release
python -m unittest discover -s tests
npm run check
npm run build
```

Stage the intended source files explicitly, review `git diff --cached`, and make
a descriptive commit, for example `git commit -m "Track website versions and
release history"`. Include new files; leave unrelated local edits and generated
`build/` output out of the commit. Push with `git push -u origin dev` when ready
to share the work. Dev CI validates and archives the website without deploying it.

## Promote 0.2.0 to production

Run these steps only when the release is ready. Start with committed development
work and a clean working tree.

1. Prepare release metadata on `dev`:

   ```sh
   git switch dev
   git pull --ff-only origin dev
   npm version 0.2.0 --no-git-tag-version
   ```

   In `src/lib/release-history.json`, finalize the 0.2.0 changes, change its status
   to `released`, and set `releasedOn` to the intended release date. Preserve the
   0.1.0 entry. If publication is delayed, adjust the date before tagging.

2. Validate and preview the prepared release:

   ```sh
   npm run release:check -- --tag v0.2.0
   npm run test:release
   python -m unittest discover -s tests
   npm run check
   npm run build
   npm run preview
   ```

   Inspect the footer and `/docs/#revision-history`. The footer should say
   `Website v0.2.0`; the history should show the release date. Check the affected
   generator functionality as appropriate for the release.

3. Commit the preparation and push `dev`:

   ```sh
   git add package.json package-lock.json src/lib/release-history.json
   git diff --cached
   git commit -m "Prepare website v0.2.0"
   git push origin dev
   ```

4. Open a pull request from `dev` to `main`. Require the website `build` check to
   pass, review the changes, and merge using a **merge commit** so both long-lived
   branches retain shared history. PRs targeting `main` must contain stable
   release metadata. The website still does not deploy at merge time.

   The separate **Build HLCL libraries** workflow does run on the push to `main`
   and updates the rolling `latest` library download. Wait for that workflow and
   the website checks to pass before tagging.

5. Tag the reviewed release commit on `main` and push only that tag:

   ```sh
   git switch main
   git pull --ff-only origin main
   git log -1 --oneline
   npm run release:check -- --tag v0.2.0
   git tag -a v0.2.0 -m "Website v0.2.0"
   git push origin v0.2.0
   ```

   Confirm the displayed commit is the reviewed release. **Pushing this tag is
   the website production promotion.** Do not move or reuse a published version
   tag, and do not push a tag for a development version.

6. Watch **Website checks and release** in GitHub Actions. It verifies the tag
   matches the package version, the history is released and dated, and the tagged
   commit is an ancestor of `origin/main`. It then runs checks, builds the site,
   deploys to Pages, and creates the `v0.2.0` GitHub Release with the history notes
   and `website-v0.2.0.zip`. Verify the live footer and revision history after the
   job succeeds.

Website releases use `--latest=false` so the existing rolling library release
continues to own `/releases/latest/download/hlcl-build-output.zip`. The website
archive contains the deployable site; the rolling library archive contains the
generated Altium libraries. Website version tags are immutable; the existing
library-only `latest` tag continues to move on pushes to `main`.

## Start the next development cycle

After promotion, bring the merge commit back to `dev`, choose the next version,
and add a new unreleased entry at the start of the history. For example:

```sh
git switch dev
git merge --ff-only main
npm version 0.3.0-dev --no-git-tag-version
```

Add a 0.3.0 entry with `status: "unreleased"`, `releasedOn: null`, and a brief
description of the planned cycle. Preserve the released 0.2.0 notes and date.
Run `npm run release:check`, commit the three metadata files with a message such
as `Start 0.3.0 development`, and push `dev`.

## Deployment setup, retries, and rollback

In repository **Settings → Pages**, use **GitHub Actions** as the publishing
source. Keep the production custom domain configured there. In the
`github-pages` environment, allow version tags matching `v*` to deploy; an
environment restricted only to the `main` branch will reject tag deployments.
Protect `main` with pull requests and the website build check. These are
repository settings; committing the workflow does not change them.

For a failed run, fix the cause and rerun the workflow if the tagged source is
still correct. If source changes are needed after publication, make a new patch
release through `dev` and `main` instead of replacing the old tag.

To redeploy a previously published version, select its tag with GitHub CLI:

```sh
gh workflow run pages.yml --ref v0.2.0
```

This rebuilds and redeploys that tag, repeats the production checks, and preserves
an existing GitHub Release. It can roll the website back to an earlier version
that contains this workflow. It does not roll back the separate rolling library
download. The original 0.1.0 predates this workflow and cannot be redeployed this
way without a separate recovery procedure. Selecting a branch only runs checks.

See GitHub's [Pages workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
and [`gh release create` reference](https://cli.github.com/manual/gh_release_create)
for the deployment environment and release flags used here.
