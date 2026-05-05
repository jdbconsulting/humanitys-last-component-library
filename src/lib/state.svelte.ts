/**
 * Global, browser-only configurator state.
 *
 * The persisted shape is wrapped around a canonical `BuildConfig` (defined
 * in `./schema.ts`). `BuildConfig` is the only thing crossing the Python ↔
 * web-app boundary today, and is the planned input to a future
 * `python build.py --config foo.json`. UI-only fields (the active preset id,
 * the user-typed configuration file stem) live in a sibling `ui` block so they
 * can evolve independently of the canonical contract.
 *
 * One Svelte 5 class instance is exported as `appState` and shared across
 * every tab. State is persisted to `localStorage` so a refresh doesn't
 * blow away in-progress configuration. v1 envelopes (the original shape
 * used before BuildConfig was introduced) are migrated on first hydrate.
 */

import {
	buildConfigSchema,
	defaultBuildConfig,
	defaultUiSession,
	parsePersistedState,
	persistedStateSchema,
	BUILD_CONFIG_VERSION,
	STORAGE_VERSION,
	type Artifacts,
	type BuildConfig,
	type BuildStats,
	type CachedBuildStats,
	type Crosslink,
	type FamilyConfig,
	type FamilyOptionValue,
	type PersistedState,
	type Settings,
	type UiSession
} from './schema';
import { LIBRARY_CATALOG, allFamilies } from './libraries';
import { sanitizeConfigFilenameStem } from './config-filename';

const STORAGE_KEY = 'hlcl-configurator-v2';
const LEGACY_V1_STORAGE_KEY = 'hlcl-configurator-v1';

/**
 * Deep-merge for plain JSON-y objects. Arrays are replaced wholesale, scalars
 * overwrite, plain objects merge recursively. Used by `migrateV1()` to overlay
 * a v1 partial-settings blob on top of fresh defaults.
 */
function deepMerge<T>(base: T, override: unknown): T {
	if (override === undefined || override === null) return base;
	if (Array.isArray(override)) return override as unknown as T;
	if (typeof override !== 'object') return override as T;
	if (typeof base !== 'object' || base === null || Array.isArray(base)) {
		return override as T;
	}
	const out: Record<string, unknown> = { ...(base as Record<string, unknown>) };
	for (const [k, v] of Object.entries(override as Record<string, unknown>)) {
		out[k] = deepMerge((base as Record<string, unknown>)[k], v);
	}
	return out as T;
}

// `PresetDelta` (the partial-overlay shape that used to power `applyPreset`)
// has been retired. Presets are now full `BuildConfig` documents loaded from
// `hlcl/presets/*.json` and applied wholesale; see `applyPreset()` below.

/**
 * Stable 32-bit FNV-1a fingerprint of a `BuildConfig`. Used to gate
 * `ui.build_stats` freshness — equal hashes mean the in-memory config
 * matches the one that produced the cached stats; mismatch means the
 * user has edited something and the banner should fade to "???".
 *
 * The `crosslinks` field is intentionally excluded: it doesn't change
 * what the build emits, so editing crosslinks shouldn't invalidate
 * stats from a previous run.
 */
function configHash(cfg: BuildConfig): string {
	const subset = {
		schema_version: cfg.schema_version,
		families: cfg.families,
		settings: cfg.settings,
		artifacts: cfg.artifacts
	};
	const s = JSON.stringify(subset);
	let h = 0x811c9dc5;
	for (let i = 0; i < s.length; i++) {
		h ^= s.charCodeAt(i);
		h = Math.imul(h, 0x01000193);
	}
	return (h >>> 0).toString(16).padStart(8, '0');
}

// ---------------------------------------------------------------------------
// Default family map (catalog-aware)
// ---------------------------------------------------------------------------

function defaultFamilyConfig(familyId: string): FamilyConfig {
	const fam = allFamilies().find((f) => f.id === familyId);
	const options: Record<string, FamilyOptionValue> = {};
	const overrides: Record<string, boolean> = {};
	if (fam) {
		for (const opt of fam.options) {
			switch (opt.control.kind) {
				case 'toggle':
					options[opt.id] = opt.control.defaultValue;
					break;
				case 'select':
					options[opt.id] = opt.control.defaultValue;
					break;
				case 'multiselect':
					options[opt.id] = [...opt.control.defaultValue];
					break;
				case 'number':
					options[opt.id] = opt.control.defaultValue;
					break;
				case 'text':
					options[opt.id] = opt.control.defaultValue;
					break;
			}
			if (opt.overridesGlobal) overrides[opt.id] = false;
		}
	}
	return { enabled: false, options, overrides };
}

/**
 * Populate the catalog-derived default families dict, with a sensible
 * starter selection enabled. Used both as the initial app state and as
 * the "Factory defaults" preset baseline.
 */
function defaultFamiliesPopulated(): Record<string, FamilyConfig> {
	const out: Record<string, FamilyConfig> = {};
	for (const k of LIBRARY_CATALOG) {
		for (const s of k.subtypes) {
			for (const f of s.families) {
				out[f.id] = defaultFamilyConfig(f.id);
			}
		}
	}
	for (const id of ['panasonic-erj', 'samsung-capacitors', 'murata-ferrites']) {
		if (out[id]) out[id].enabled = true;
	}
	return out;
}

/** Bare-minimum valid `BuildConfig` plus the catalog-driven family map. */
export function defaultBuildConfigWithFamilies(): BuildConfig {
	const cfg = defaultBuildConfig();
	cfg.families = defaultFamiliesPopulated();
	return cfg;
}

/**
 * Backfill catalog-known families that aren't present in `families`. New
 * vendor families show up in the catalog the moment a `catalog.json` lands
 * on disk, but a user with stale `localStorage` (or an imported config
 * predating the new family) is missing the corresponding entry. Without
 * this backfill, `LibraryFamilyCard` reads `families[id].enabled` on an
 * undefined entry and the Libraries tab crashes with
 * `Cannot read properties of undefined (reading 'enabled')`.
 *
 * Backfilled entries land disabled (the user opted out by virtue of
 * never having seen them); known entries are preserved verbatim so
 * the user's persisted on/off state and option overrides survive.
 */
function backfillMissingFamilies(
	families: Record<string, FamilyConfig>
): Record<string, FamilyConfig> {
	const out = { ...families };
	for (const fam of allFamilies()) {
		if (!out[fam.id]) out[fam.id] = defaultFamilyConfig(fam.id);
	}
	return out;
}

// ---------------------------------------------------------------------------
// V1 → V2 localStorage migration
// ---------------------------------------------------------------------------

/**
 * The shape stored under `hlcl-configurator-v1` before BuildConfig existed.
 * Renames during migration:
 *   project              → settings (with `priority` moving under `house_footprints`)
 *   build.emit_<name>    → artifacts.<name>
 *   activePresetId       → ui.active_preset_id
 *   configName           → ui.config_name
 */
interface LegacyV1State {
	families?: Record<
		string,
		{ enabled?: boolean; options?: Record<string, unknown>; overrides?: Record<string, boolean> }
	>;
	project?: {
		priority?: string[];
		ipc?: Partial<Settings['ipc']>;
		hlcl?: Partial<Settings['hlcl']>;
		stepgen?: Partial<Settings['stepgen']>;
		colors?: Partial<Settings['colors']>;
	};
	build?: Record<string, boolean>;
	crosslinks?: unknown[];
	activePresetId?: string | null;
	configName?: string;
}

function migrateV1(raw: unknown): PersistedState | null {
	if (typeof raw !== 'object' || raw === null) return null;
	const v1 = raw as LegacyV1State;
	const baseline = defaultBuildConfigWithFamilies();

	const families: Record<string, FamilyConfig> = { ...baseline.families };
	if (v1.families) {
		for (const [k, v] of Object.entries(v1.families)) {
			if (!families[k]) continue;
			families[k] = {
				enabled: typeof v.enabled === 'boolean' ? v.enabled : families[k].enabled,
				options: { ...families[k].options, ...(v.options as Record<string, FamilyOptionValue>) },
				overrides: { ...families[k].overrides, ...(v.overrides ?? {}) }
			};
		}
	}

	const settings: Settings = {
		house_footprints: {
			priority: v1.project?.priority ?? baseline.settings.house_footprints.priority
		},
		ipc: { ...baseline.settings.ipc, ...(v1.project?.ipc ?? {}) },
		hlcl: { ...baseline.settings.hlcl, ...(v1.project?.hlcl ?? {}) },
		stepgen: { ...baseline.settings.stepgen, ...(v1.project?.stepgen ?? {}) },
		colors: deepMerge(baseline.settings.colors, v1.project?.colors)
	};

	const b = v1.build ?? {};
	const artifacts: Artifacts = {
		xls: b.emit_xls ?? baseline.artifacts.xls,
		dblib: b.emit_dblib ?? baseline.artifacts.dblib,
		footprints_json: b.emit_footprints_json ?? baseline.artifacts.footprints_json,
		house_footprints_merge:
			b.emit_house_footprints_merge ?? baseline.artifacts.house_footprints_merge,
		step_models: b.emit_step_models ?? baseline.artifacts.step_models,
		pcblib: b.emit_pcblib ?? baseline.artifacts.pcblib,
		schlib: b.emit_schlib ?? baseline.artifacts.schlib,
		// `standards_pdf` (the legacy pdflatex flag) split into separate
		// LaTeX-source / Markdown-source artifact toggles. There's no
		// faithful migration -- the new flags emit different files than
		// the old PDF target -- so we just default both to off and let
		// the user opt in on the Build tab.
		standards_tex: baseline.artifacts.standards_tex,
		standards_md: baseline.artifacts.standards_md,
		zip_output: b.zip_output ?? baseline.artifacts.zip_output
	};

	const crosslinks: Crosslink[] = Array.isArray(v1.crosslinks)
		? v1.crosslinks
				.filter((c): c is Record<string, unknown> => typeof c === 'object' && c !== null)
				.map((c) => ({
					primary_mpn: typeof c.primary_mpn === 'string' ? c.primary_mpn : '',
					primary_mfg: typeof c.primary_mfg === 'string' ? c.primary_mfg : '',
					substitute_mpn: typeof c.substitute_mpn === 'string' ? c.substitute_mpn : '',
					substitute_mfg: typeof c.substitute_mfg === 'string' ? c.substitute_mfg : '',
					notes: typeof c.notes === 'string' ? c.notes : ''
				}))
		: [];

	const config: BuildConfig = {
		schema_version: BUILD_CONFIG_VERSION,
		families,
		settings,
		artifacts,
		crosslinks
	};

	const ui: UiSession = {
		active_preset_id: null, // intentionally cleared on migration
		config_name: sanitizeConfigFilenameStem(
			typeof v1.configName === 'string' ? v1.configName : 'hlcl-build'
		),
		// Library-stats banner didn't exist pre-v2; the very next build
		// will populate it.
		build_stats: null
	};

	return { storage_version: STORAGE_VERSION, config, ui };
}

// ---------------------------------------------------------------------------
// AppState class
// ---------------------------------------------------------------------------

class AppState {
	config = $state<BuildConfig>(initialBuildConfig());
	ui = $state<UiSession>(defaultUiSession());

	/**
	 * In-memory hash of the BuildConfig taken at the moment a preset was
	 * applied. The persist effect compares the current hash against this;
	 * any mismatch flips `ui.active_preset_id` to null ("Custom").
	 *
	 * Not persisted — across reloads we can't tell whether stored state
	 * still matches the named preset, so `hydrate()` clears
	 * `ui.active_preset_id`.
	 */
	private presetSnapshotKey: string = '';

	private snapshotKey(): string {
		return JSON.stringify($state.snapshot(this.config));
	}

	/** Hydrate from localStorage. Safe to call multiple times. */
	hydrate(): void {
		if (typeof window === 'undefined') return;

		// Try v2 first.
		try {
			const raw = localStorage.getItem(STORAGE_KEY);
			if (raw) {
				const parsed = parsePersistedState(JSON.parse(raw));
				if (parsed.ok && parsed.value) {
					this.applyPersistedState(parsed.value);
					return;
				}
			}
		} catch {
			/* malformed v2 — fall through to v1 migration */
		}

		// Fall back to v1 migration.
		try {
			const rawV1 = localStorage.getItem(LEGACY_V1_STORAGE_KEY);
			if (rawV1) {
				const migrated = migrateV1(JSON.parse(rawV1));
				if (migrated) {
					this.applyPersistedState(migrated);
					this.persist();
					localStorage.removeItem(LEGACY_V1_STORAGE_KEY);
					return;
				}
			}
		} catch {
			/* malformed v1 — give up, keep defaults */
		}
	}

	private applyPersistedState(state: PersistedState): void {
		// Clone via Zod parse (already validated, but parse() also strips
		// unknown keys + applies `.default()` so the in-memory object is
		// always canonical).
		const reparsed = persistedStateSchema.parse(state);
		this.config = {
			...reparsed.config,
			// Catalogs grow over time; persisted state from before a new
			// family landed misses its entry. Backfill before the
			// Libraries tab tries to render a card for it.
			families: backfillMissingFamilies(reparsed.config.families)
		};
		// Don't restore active_preset_id across reloads — we can't reliably
		// know if state still matches the named preset, so we conservatively
		// show "Custom" until the user re-applies.
		this.ui = {
			...reparsed.ui,
			active_preset_id: null,
			config_name: sanitizeConfigFilenameStem(reparsed.ui.config_name ?? '')
		};
	}

	/** Snapshot the current state as a plain JSON-safe object. */
	snapshot(): PersistedState {
		return {
			storage_version: STORAGE_VERSION,
			config: $state.snapshot(this.config) as BuildConfig,
			ui: $state.snapshot(this.ui) as UiSession
		};
	}

	/** Snapshot just the canonical config (for download / hand-off to Python). */
	snapshotConfig(): BuildConfig {
		return $state.snapshot(this.config) as BuildConfig;
	}

	persist(): void {
		if (typeof window === 'undefined') return;
		try {
			localStorage.setItem(STORAGE_KEY, JSON.stringify(this.snapshot()));
		} catch {
			/* quota / private mode — ignore */
		}
	}

	resetAll(): void {
		this.config = initialBuildConfig();
		this.ui = defaultUiSession();
		this.presetSnapshotKey = '';
	}

	/**
	 * Apply a preset's `BuildConfig` wholesale. The `presetConfig` argument
	 * is the full canonical config straight out of
	 * `hlcl/presets/<id>.json::config` — every family is enumerated
	 * (`enabled` true or false), every setting populated, every artifact
	 * flag set. We:
	 *
	 *   1. Backfill catalog-known families that the preset file itself
	 *      doesn't mention. Older preset files predating a freshly-added
	 *      vendor family land that family disabled (the conservative
	 *      default for presets that haven't yet been refreshed for the
	 *      new family).
	 *   2. Preserve the user's existing crosslinks — they're user data,
	 *      not a configuration knob, and shouldn't be wiped by a preset.
	 *   3. Re-parse through Zod so a malformed `_generated/presets.ts`
	 *      can never silently slip a bad value into `appState`.
	 */
	applyPreset(presetId: string, presetTitle: string, presetConfig: BuildConfig): void {
		const families = backfillMissingFamilies(presetConfig.families);
		const crosslinks = $state.snapshot(this.config.crosslinks) as Crosslink[];

		this.config = buildConfigSchema.parse({
			schema_version: BUILD_CONFIG_VERSION,
			families,
			settings: presetConfig.settings,
			artifacts: presetConfig.artifacts,
			crosslinks
		});

		// Carry the cached build stats across preset application: the
		// `config_hash` check elsewhere flips them to "stale" when the
		// hashes diverge, but if the user round-trips through Preset N
		// → Preset M → Preset N the hash matches again and the numbers
		// reappear. Clearing here would force a redundant rebuild.
		this.ui = {
			...this.ui,
			active_preset_id: presetId,
			config_name: sanitizeConfigFilenameStem(presetTitle)
		};
		this.presetSnapshotKey = this.snapshotKey();
	}

	/**
	 * Import a previously-exported configuration JSON. Validates against the
	 * canonical schema; returns an error string list on failure, or null on
	 * success.
	 */
	importConfig(raw: unknown): string[] | null {
		// Two acceptable shapes:
		//  (a) a bare `BuildConfig` (what the Generate tab's
		//      "Download configuration.json" button emits today)
		//  (b) a full `PersistedState` envelope (storage_version + config + ui)
		if (typeof raw !== 'object' || raw === null) return ['Not a valid configuration object.'];
		const obj = raw as Record<string, unknown>;
		if (obj.storage_version) {
			const env = parsePersistedState(raw);
			if (!env.ok || !env.value) return env.errors ?? ['unknown error'];
			this.applyPersistedState(env.value);
		} else {
			const cfg = buildConfigSchema.safeParse(raw);
			if (!cfg.success) {
				return cfg.error.issues.map((iss) => {
					const path = iss.path.length > 0 ? iss.path.join('.') : '<root>';
					return `${path}: ${iss.message}`;
				});
			}
			// Same backfill rationale as `applyPersistedState`: imported
			// configs from before a new catalog family landed are missing
			// its entry, which would crash the Libraries tab.
			this.config = {
				...cfg.data,
				families: backfillMissingFamilies(cfg.data.families)
			};
			this.ui = {
				...this.ui,
				active_preset_id: null,
				config_name: sanitizeConfigFilenameStem('imported-configuration')
				// Cached build_stats are preserved; their config_hash will
				// either match the imported config (round-trip) or stay
				// stale until a fresh build.
			};
		}
		this.presetSnapshotKey = '';
		return null;
	}

	/**
	 * If the current state has drifted from the named preset, clear the
	 * preset id so the UI shows "Custom configuration".
	 */
	detectCustomisation(): void {
		if (this.ui.active_preset_id === null) return;
		if (this.snapshotKey() !== this.presetSnapshotKey) {
			this.ui = {
				...this.ui,
				active_preset_id: null,
				config_name: sanitizeConfigFilenameStem('custom')
			};
		}
	}

	enabledFamilyIds(): string[] {
		return Object.entries(this.config.families)
			.filter(([, v]) => v.enabled)
			.map(([k]) => k);
	}

	/**
	 * Cache the library-stats triple alongside a hash of the
	 * `BuildConfig` that produced it. Called by `GenerateTab` after
	 * `runBuild()` succeeds; the snapshot is the moment-in-time config
	 * the build saw, NOT the live one (the user might have already
	 * started editing in another tab while the build was running).
	 */
	setBuildStats(stats: BuildStats, builtConfig: BuildConfig): void {
		const cached: CachedBuildStats = {
			stats,
			config_hash: configHash(builtConfig)
		};
		this.ui = { ...this.ui, build_stats: cached };
	}

	/**
	 * `true` iff the cached `ui.build_stats` was produced from a
	 * `BuildConfig` whose hash still matches the live one — i.e. the
	 * banner numbers are still authoritative. Returns `false` both
	 * when there's no cached stats at all and when the cached hash has
	 * drifted from the live config (a downstream-tab edit took place).
	 */
	buildStatsAreFresh(): boolean {
		const cached = this.ui.build_stats;
		if (!cached) return false;
		return cached.config_hash === configHash($state.snapshot(this.config) as BuildConfig);
	}

	addCrosslink(): void {
		this.config.crosslinks = [
			...this.config.crosslinks,
			{
				primary_mpn: '',
				primary_mfg: '',
				substitute_mpn: '',
				substitute_mfg: '',
				notes: ''
			}
		];
	}

	removeCrosslinkAt(index: number): void {
		this.config.crosslinks = this.config.crosslinks.filter((_, i) => i !== index);
	}
}

function initialBuildConfig(): BuildConfig {
	return defaultBuildConfigWithFamilies();
}

export const appState = new AppState();
