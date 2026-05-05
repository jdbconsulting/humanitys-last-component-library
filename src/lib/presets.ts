/**
 * Named configuration presets — runtime view.
 *
 * The source of truth for every preset is one
 * `hlcl/presets/<id>.json` file. The Vite plugin in
 * `vite/plugins/hlcl-build-assets.ts` discovers, validates, and merges
 * those into `_generated/presets.ts` on every dev save / production
 * build (and via the standalone `npm run regen` script). This file
 * then exposes a thin runtime view tailored to what the PresetsTab
 * needs.
 *
 * Adding / editing a preset is therefore a pure-data change: drop a
 * new `hlcl/presets/<id>.json` file (or edit an existing one) and the
 * Presets tab grows / updates a card on the next dev reload — no
 * edits to this file required.
 *
 * File shape — see `presetFileSchema` in `./schema.ts`. Each preset:
 *
 *   - `id`         stable id used in localStorage; renaming is breaking.
 *   - `title`      formatted display name (e.g. "Everything · the kitchen sink").
 *   - `tagline`    short ALL-CAPS pill rendered next to the title.
 *   - `description` paragraph blurb.
 *   - `bullets`    green-checkmark bullet list rendered on the card.
 *   - `sort_order` integer; lower comes first.
 *   - `config`     a full `BuildConfig` overlaid wholesale on apply (the
 *                  legacy `PresetDelta` shape has been retired). Crosslinks
 *                  are intentionally preserved across `applyPreset()`.
 */

import { PRESET_FILES } from './_generated/presets';
import type { PresetFile } from './schema';

export type Preset = PresetFile;

/** Read-only list of presets, ordered by `sort_order` then `id`. */
export const PRESETS: readonly Preset[] = PRESET_FILES;

export function getPreset(id: string): Preset | undefined {
	return PRESETS.find((p) => p.id === id);
}
