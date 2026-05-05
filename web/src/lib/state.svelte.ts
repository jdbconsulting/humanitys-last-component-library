/**
 * Global, browser-only configurator state. One Svelte 5 class instance is
 * exported as `appState` and shared across every tab. State is persisted to
 * `localStorage` so a refresh doesn't blow away in-progress configuration.
 */

import { LIBRARY_CATALOG, allFamilies } from './libraries';

const STORAGE_KEY = 'hlcl-configurator-v1';

export type FamilyOptionValue = boolean | number | string | string[];

export interface FamilyState {
	enabled: boolean;
	options: Record<string, FamilyOptionValue>;
	overrides: Record<string, boolean>; // optionId → true if a per-family value is in use (vs global)
}

export interface ProjectSettings {
	priority: string[];
	ipc: {
		fabrication_tolerance_mm: number;
		placement_tolerance_mm: number;
	};
	hlcl: {
		pad_corner_radius_percent: number;
		solder_mask_expansion_mm: number;
		min_solder_mask_sliver_mm: number;
		outline_line_width_mm: number;
		max_crosshair_half_arm_mm: number;
		component_body_standoff_mm: number;
	};
	stepgen: {
		default_fillet_radius_mm: number;
		resc_metal_thickness_fraction: number;
		resc_metal_thickness_floor_mm: number;
	};
	colors: {
		default: { body: [number, number, number] };
		capc: { body: [number, number, number]; terminal: [number, number, number] };
		indc: { body: [number, number, number]; terminal: [number, number, number] };
		fb: { body: [number, number, number]; terminal: [number, number, number] };
		resc: {
			substrate: [number, number, number];
			passivation: [number, number, number];
			terminal: [number, number, number];
		};
	};
}

export interface BuildSettings {
	emit_xls: boolean;
	emit_dblib: boolean;
	emit_footprints_json: boolean;
	emit_house_footprints_merge: boolean;
	emit_step_models: boolean;
	emit_pcblib: boolean;
	emit_schlib: boolean;
	emit_standards_pdf: boolean;
	zip_output: boolean;
}

export interface CrosslinkRow {
	id: string;
	primary_mpn: string;
	primary_mfg: string;
	substitute_mpn: string;
	substitute_mfg: string;
	notes: string;
}

export interface PersistedState {
	families: Record<string, FamilyState>;
	project: ProjectSettings;
	build: BuildSettings;
	crosslinks: CrosslinkRow[];
	/** Id of the last preset applied via the Presets tab, or null if the user has freely customised. */
	activePresetId: string | null;
	/** User-editable display name for this configuration. */
	configName: string;
}

/**
 * Shape a preset takes when it's applied. Each top-level key is independently
 * optional: a preset may only set a few families, or only override a couple of
 * project knobs, or only flip build flags.
 */
export interface PresetDelta {
	/**
	 * Family ids to enable. Any family id present is set to `enabled = true`.
	 * Anything not listed is set to `enabled = false`. Per-family option
	 * overrides may be specified in `familyOptions` below.
	 */
	families?: string[];
	/** Per-family option overrides keyed by family id then option id. */
	familyOptions?: Record<string, Record<string, FamilyOptionValue>>;
	/** Per-family `Use global` ↔ `Override` flags, mirroring `FamilyState.overrides`. */
	familyOverrides?: Record<string, Record<string, boolean>>;
	/** Project-settings deltas — partial merge into `project.ipc`, etc. */
	project?: {
		ipc?: Partial<ProjectSettings['ipc']>;
		hlcl?: Partial<ProjectSettings['hlcl']>;
		stepgen?: Partial<ProjectSettings['stepgen']>;
		priority?: string[];
	};
	/** Build-settings deltas — only the listed flags are flipped. */
	build?: Partial<BuildSettings>;
}

function defaultProjectSettings(): ProjectSettings {
	return {
		priority: [
			'panasonic-erj',
			'panasonic-era-a',
			'panasonic-era-v',
			'panasonic-era-p',
			'ohmite-kdv',
			'samsung-capacitors',
			'tdk-capacitors',
			'murata-gcm',
			'murata-grm',
			'murata-ferrite'
		],
		ipc: { fabrication_tolerance_mm: 0.1, placement_tolerance_mm: 0.05 },
		hlcl: {
			pad_corner_radius_percent: 25,
			solder_mask_expansion_mm: 0.05,
			min_solder_mask_sliver_mm: 0.1,
			outline_line_width_mm: 0.1,
			max_crosshair_half_arm_mm: 0.5,
			component_body_standoff_mm: 0.0
		},
		stepgen: {
			default_fillet_radius_mm: 0.05,
			resc_metal_thickness_fraction: 0.1,
			resc_metal_thickness_floor_mm: 0.02
		},
		colors: {
			default: { body: [160, 160, 160] },
			capc: { body: [184, 134, 11], terminal: [204, 204, 204] },
			indc: { body: [38, 77, 148], terminal: [204, 204, 204] },
			fb: { body: [38, 77, 148], terminal: [204, 204, 204] },
			resc: {
				substrate: [158, 158, 158],
				passivation: [23, 23, 23],
				terminal: [128, 128, 128]
			}
		}
	};
}

function defaultBuildSettings(): BuildSettings {
	return {
		emit_xls: true,
		emit_dblib: true,
		emit_footprints_json: true,
		emit_house_footprints_merge: true,
		emit_step_models: true,
		emit_pcblib: true,
		emit_schlib: true,
		emit_standards_pdf: false,
		zip_output: true
	};
}

function defaultFamilyState(familyId: string): FamilyState {
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

function defaultFamilies(): Record<string, FamilyState> {
	const out: Record<string, FamilyState> = {};
	for (const k of LIBRARY_CATALOG) {
		for (const s of k.subtypes) {
			for (const f of s.families) {
				out[f.id] = defaultFamilyState(f.id);
			}
		}
	}
	// Prepopulate a sensible default selection.
	for (const id of ['panasonic-erj', 'samsung-capacitors', 'murata-ferrites']) {
		if (out[id]) out[id].enabled = true;
	}
	return out;
}

class AppState {
	families = $state<Record<string, FamilyState>>(defaultFamilies());
	project = $state<ProjectSettings>(defaultProjectSettings());
	build = $state<BuildSettings>(defaultBuildSettings());
	crosslinks = $state<CrosslinkRow[]>([]);
	activePresetId = $state<string | null>(null);
	configName = $state<string>('My configuration');

	/**
	 * In-memory hash of `families + project + build` taken at the moment a
	 * preset was applied. The persist effect compares the current hash against
	 * this; any mismatch flips `activePresetId` to null ("Custom configuration").
	 *
	 * Not persisted — across reloads we can't tell whether stored state still
	 * matches the named preset, so `hydrate()` clears `activePresetId`.
	 */
	private presetSnapshotKey: string = '';

	private snapshotKey(): string {
		return JSON.stringify([
			$state.snapshot(this.families),
			$state.snapshot(this.project),
			$state.snapshot(this.build)
		]);
	}

	/**
	 * Hydrate from localStorage. Safe to call multiple times; later calls overwrite
	 * the in-memory state. Called from `+layout.svelte` on the client.
	 */
	hydrate(): void {
		if (typeof window === 'undefined') return;
		try {
			const raw = localStorage.getItem(STORAGE_KEY);
			if (!raw) return;
			const parsed: Partial<PersistedState> = JSON.parse(raw);
			if (parsed.families) {
				const merged = defaultFamilies();
				for (const [k, v] of Object.entries(parsed.families)) {
					if (merged[k]) merged[k] = { ...merged[k], ...v };
				}
				this.families = merged;
			}
			if (parsed.project) this.project = { ...defaultProjectSettings(), ...parsed.project };
			if (parsed.build) this.build = { ...defaultBuildSettings(), ...parsed.build };
			if (parsed.crosslinks) this.crosslinks = parsed.crosslinks;
			// Don't restore activePresetId across reloads — we have no reliable way
			// to know if the persisted state still matches the named preset's
			// expected state, so we conservatively show "Custom configuration"
			// on the Presets tab until the user re-applies.
			this.activePresetId = null;
			if (parsed.configName) this.configName = parsed.configName;
		} catch {
			/* malformed storage — ignore */
		}
	}

	/** Snapshot the current configuration as a plain object suitable for JSON or post-message export. */
	snapshot(): PersistedState {
		return {
			families: $state.snapshot(this.families) as Record<string, FamilyState>,
			project: $state.snapshot(this.project) as ProjectSettings,
			build: $state.snapshot(this.build) as BuildSettings,
			crosslinks: $state.snapshot(this.crosslinks) as CrosslinkRow[],
			activePresetId: this.activePresetId,
			configName: this.configName
		};
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
		this.families = defaultFamilies();
		this.project = defaultProjectSettings();
		this.build = defaultBuildSettings();
		this.crosslinks = [];
		this.activePresetId = null;
		this.configName = 'My configuration';
		this.presetSnapshotKey = '';
	}

	/**
	 * Apply a preset on top of factory defaults. The behaviour is "start fresh,
	 * then apply": every family is reset before the preset's `families` list is
	 * enabled, so two presets applied back-to-back don't accumulate enabled
	 * families. Cross-links are intentionally preserved — they're user data,
	 * not a configuration knob.
	 */
	applyPreset(presetId: string, presetName: string, delta: PresetDelta): void {
		const freshFamilies = defaultFamilies();
		if (delta.families) {
			for (const id of delta.families) {
				if (freshFamilies[id]) freshFamilies[id].enabled = true;
			}
		}
		if (delta.familyOptions) {
			for (const [famId, opts] of Object.entries(delta.familyOptions)) {
				const fam = freshFamilies[famId];
				if (!fam) continue;
				for (const [optId, value] of Object.entries(opts)) {
					fam.options[optId] = Array.isArray(value) ? [...value] : value;
				}
			}
		}
		if (delta.familyOverrides) {
			for (const [famId, overs] of Object.entries(delta.familyOverrides)) {
				const fam = freshFamilies[famId];
				if (!fam) continue;
				for (const [optId, on] of Object.entries(overs)) {
					fam.overrides[optId] = on;
				}
			}
		}
		this.families = freshFamilies;

		const freshProject = defaultProjectSettings();
		if (delta.project?.ipc) Object.assign(freshProject.ipc, delta.project.ipc);
		if (delta.project?.hlcl) Object.assign(freshProject.hlcl, delta.project.hlcl);
		if (delta.project?.stepgen) Object.assign(freshProject.stepgen, delta.project.stepgen);
		if (delta.project?.priority) freshProject.priority = [...delta.project.priority];
		this.project = freshProject;

		this.build = { ...defaultBuildSettings(), ...(delta.build ?? {}) };
		this.activePresetId = presetId;
		this.configName = presetName;
		this.presetSnapshotKey = this.snapshotKey();
	}

	/**
	 * Import a previously exported PersistedState JSON. Validates loosely and
	 * merges into defaults so unknown/future fields don't break anything.
	 * Returns an error string on failure, or null on success.
	 */
	importConfig(raw: unknown): string | null {
		if (typeof raw !== 'object' || raw === null) return 'Not a valid configuration object.';
		const parsed = raw as Partial<PersistedState>;
		try {
			if (parsed.families) {
				const merged = defaultFamilies();
				for (const [k, v] of Object.entries(parsed.families)) {
					if (merged[k]) merged[k] = { ...merged[k], ...v };
				}
				this.families = merged;
			}
			if (parsed.project) this.project = { ...defaultProjectSettings(), ...parsed.project };
			if (parsed.build) this.build = { ...defaultBuildSettings(), ...parsed.build };
			if (Array.isArray(parsed.crosslinks)) this.crosslinks = parsed.crosslinks;
			this.configName = parsed.configName || 'Imported configuration';
			this.activePresetId = null;
			this.presetSnapshotKey = '';
			return null;
		} catch (e) {
			return e instanceof Error ? e.message : String(e);
		}
	}

	/**
	 * Compare the current state against the snapshot taken at preset-apply time.
	 * If they differ, the user has wandered off the preset — clear it.
	 *
	 * Called from the layout's persist effect after every state mutation.
	 */
	detectCustomisation(): void {
		if (this.activePresetId === null) return;
		if (this.snapshotKey() !== this.presetSnapshotKey) {
			this.activePresetId = null;
			this.configName = 'Custom';
		}
	}

	enabledFamilyIds(): string[] {
		return Object.entries(this.families)
			.filter(([, v]) => v.enabled)
			.map(([k]) => k);
	}

	addCrosslink(): void {
		const id = `xl-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
		this.crosslinks.push({
			id,
			primary_mpn: '',
			primary_mfg: '',
			substitute_mpn: '',
			substitute_mfg: '',
			notes: ''
		});
	}

	removeCrosslink(id: string): void {
		this.crosslinks = this.crosslinks.filter((r) => r.id !== id);
	}
}

export const appState = new AppState();
