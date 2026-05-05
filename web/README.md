# `web/` — HLCL configurator

Static SvelteKit + Tailwind 4 web app that drives the HLCL build pipeline from
the browser via [Pyodide]. No server runtime — the production bundle is a
plain folder of static files suitable for GitHub Pages, Cloudflare Pages,
Netlify, S3, …

## Project layout

```
web/
├── src/
│   ├── app.html                  HTML shell + Inter / JetBrains Mono fonts
│   ├── lib/
│   │   ├── assets/favicon.svg    Custom HLCL favicon
│   │   ├── components/           Header, Console, Toggle, NumberField, …
│   │   │   └── tabs/             One component per workflow tab
│   │   ├── console.svelte.ts     Reactive log buffer (Pyodide stdout/stderr sink)
│   │   ├── libraries.ts          Vendor family catalog (drives the Libraries tab)
│   │   ├── pyodide.ts            Lazy CDN loader for Pyodide
│   │   └── state.svelte.ts       Persisted app state (localStorage)
│   └── routes/
│       ├── +layout.svelte        Header / footer / state hydrate + persist
│       ├── +layout.ts            prerender = true, trailingSlash = always
│       ├── +page.svelte          Landing page
│       └── configure/+page.svelte  5-tab workflow with persistent console
└── svelte.config.js              adapter-static + paths.base = /be-done-with-it-passives
```

## Workflow tabs

1. **Presets** — start from a named template (consumer, automotive, precision,
   high-voltage, everything, factory defaults). Applying a preset overlays a
   `PresetDelta` on top of factory defaults: it sets enabled families,
   per-family option overrides, project-settings deltas, and build-output
   flags. Crosslinks are intentionally preserved — they're user data.
   Edits in any later tab automatically flip the badge to **Custom
   configuration**. Definitions live in `src/lib/presets.ts`.
2. **Libraries** — pick component family libraries. Organized by component
   type (resistor / capacitor / ferrite / inductor) and subtype (thick film,
   thin film, MLCC commercial, …). Each family is expandable for per-family
   options and overrides; numeric overrides default to "Use global".
3. **Project Settings** — mirrors `house/settings.toml` (IPC-7351B
   tolerances, HLCL drawing standards, STEP geometry knobs, vendor priority
   order, family colours).
4. **Build Settings** — toggle which artifacts the in-browser build will
   emit (vendor `.xls` / `.DbLib`, footprints JSON, STEP, `house.PcbLib`,
   `house.SchLib`, standards PDF, zip).
5. **Crosslinks** — define MPN/MFG substitutes for downstream BOM tools.
6. **Preview** — review the generated `house/settings.toml`, the ordered
   build plan, and the final JSON configuration before generating.
7. **Generate** — load Pyodide, run hello-world smoke tests, download a JSON
   snapshot of the configuration. The full build pipeline lives in the repo
   root's [`build.py`](../build.py); because every step runs in-process
   (no `subprocess`, no `make`), Pyodide can drive it directly via
   `pyimport("build"); build.build_all(root="/work")` once the source tree
   is mounted in its in-memory FS.

A persistent **Python console** dock lives at the bottom of the configure
page; collapse it via the chevron in its header.

State is persisted to `localStorage` under `hlcl-configurator-v1`. Visiting
the site again restores the last configuration.

## Developing

```sh
npm install
npm run dev          # http://localhost:5173
```

Useful npm scripts:

```sh
npm run check        # svelte-check (TypeScript + Svelte diagnostics)
npm run lint         # prettier --check + eslint
npm run format       # prettier --write
npm run build        # production static build into ./build/
npm run preview      # serve ./build/ locally
```

## Building for GitHub Pages

`svelte.config.js` reads `BASE_PATH` from the environment so dev runs at `/`
and CI builds at the repo path. The repo is hosted at
`https://jdbrinton.github.io/be-done-with-it-passives/` so the default base
path is `/be-done-with-it-passives`.

```sh
# Default (matches the repo's GitHub Pages URL)
NODE_ENV=production npm run build

# Different base path (e.g. forks)
NODE_ENV=production BASE_PATH=/my-fork npm run build

# User / org page (no base path)
NODE_ENV=production BASE_PATH= npm run build
```

The `build/` directory is what GitHub Pages serves. It contains:

- `index.html` and `configure/index.html` (prerendered)
- `404.html` (SPA fallback for client-only routes)
- `_app/` — the JS / CSS bundle
- `.nojekyll` — opt out of Jekyll's underscore-prefix munging (required for
  the `_app/` directory to be served)

### Suggested GitHub Actions workflow

Drop the following into `.github/workflows/pages.yml` to redeploy on every
push to `main`:

```yaml
name: Deploy web → Pages
on:
  push:
    branches: [main]
permissions:
  contents: read
  pages: write
  id-token: write
jobs:
  build-deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '22', cache: 'npm', cache-dependency-path: web/package-lock.json }
      - run: npm ci
        working-directory: web
      - run: npm run build
        working-directory: web
        env:
          NODE_ENV: production
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with: { path: web/build }
      - id: deployment
        uses: actions/deploy-pages@v4
```

[Pyodide]: https://pyodide.org
