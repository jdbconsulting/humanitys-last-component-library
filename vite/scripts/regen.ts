/**
 * Standalone build-asset regenerator.
 *
 * Run via `tsx vite/scripts/regen.ts`. Wired into the `prepare` (post-install)
 * and `precheck` npm scripts so a fresh `git clone && npm install && npm run
 * check` Just Works — no need to first run `npm run dev` to populate the
 * generated catalog. Inside `npm run dev` and `npm run build` the same
 * regeneration is driven by the Vite plugin in `vite/plugins/hlcl-build-assets.ts`.
 *
 * Both code paths call the SAME `regenerateBuildAssets()` function, so
 * the artefact emitted on disk is byte-identical regardless of how it
 * was produced.
 */

import { regenerateBuildAssets } from '../plugins/hlcl-build-assets.js';

await regenerateBuildAssets('npm script');
