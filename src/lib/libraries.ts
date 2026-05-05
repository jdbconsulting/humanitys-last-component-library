/**
 * Vendor family catalog (runtime view).
 *
 * The static, persisted source-of-truth lives as one
 * `hlcl/vendors/<mfg>/<family>/catalog.json` per family. The Vite plugin in
 * `vite/plugins/hlcl-build-assets.ts` discovers, validates, and merges
 * those into `_generated/catalog.ts` on every dev save / production build
 * (and via the standalone `npm run regen` script). This file then turns
 * that flat list into the `KindGroup → SubtypeGroup → FamilyDef` tree the
 * Libraries tab renders, and tacks on the "common" options (densities,
 * sizes, pad-radius override) that every family gets for free.
 *
 * Adding a new vendor family is therefore a pure-data change: drop a new
 * `hlcl/vendors/<mfg>/<family>/catalog.json` and the Libraries tab grows
 * a new card on the next dev reload — no edits to this file required.
 */

import { CATALOG_ENTRIES } from './_generated/catalog';
import type {
	ComponentKind,
	FamilyCatalogEntry,
	FamilyOptionCatalog,
	FamilyOptionControlCatalog
} from './schema';

export type { ComponentKind } from './schema';

export interface FamilyOption {
	id: string;
	label: string;
	help?: string;
	control:
		| { kind: 'toggle'; defaultValue: boolean }
		| { kind: 'select'; choices: { id: string; label: string }[]; defaultValue: string }
		| {
				kind: 'multiselect';
				choices: { id: string; label: string }[];
				defaultValue: string[];
		  }
		| {
				kind: 'number';
				defaultValue: number;
				min?: number;
				max?: number;
				step?: number;
				unit?: string;
		  }
		| { kind: 'text'; defaultValue: string; placeholder?: string };
	/** When true, the option offers a "Use global" choice in addition to its own value. */
	overridesGlobal?: boolean;
}

export interface FamilyDef {
	/** Stable id matching the build target name, e.g. `panasonic-erj`. */
	id: string;
	/** Display name. */
	name: string;
	/** Manufacturer (Panasonic, Murata, …). */
	manufacturer: string;
	/** Short blurb shown in the family card. */
	summary: string;
	/** Per-family options shown when the card is expanded. */
	options: FamilyOption[];
}

export interface SubtypeGroup {
	id: string;
	label: string;
	families: FamilyDef[];
}

export interface KindGroup {
	id: ComponentKind;
	label: string;
	subtypes: SubtypeGroup[];
}

// ---------------------------------------------------------------------------
// Hardcoded UI taxonomy: kind labels + render order.
// ---------------------------------------------------------------------------
//
// The four-kind taxonomy is closed (see `componentKindSchema` in schema.ts);
// adding a new top-level kind is a coordinated change that touches Python
// build templates, the schema, and this file. Everything BELOW kind level
// (subtypes, families, options) flows from catalog.json.

const KIND_ORDER: ComponentKind[] = ['resistor', 'capacitor', 'ferrite', 'inductor'];

const KIND_LABELS: Record<ComponentKind, string> = {
	resistor: 'Resistors',
	capacitor: 'Capacitors',
	ferrite: 'Ferrite beads',
	inductor: 'Inductors'
};

// ---------------------------------------------------------------------------
// Common per-family options applied to every catalog entry.
// ---------------------------------------------------------------------------

const ALL_DENSITY_LEVELS: ('L' | 'N' | 'M')[] = ['L', 'N', 'M'];

const DENSITY_CHOICES = [
	{ id: 'L', label: 'L (Least)' },
	{ id: 'N', label: 'N (Nominal)' },
	{ id: 'M', label: 'M (Most)' }
];

/** Imperial EIA chip-size code → label with IEC metric (L×W mm code) in parentheses. */
export const EIA_CASE_SIZE_LABELS: Record<string, string> = {
	'01005': '01005 (0402)',
	'0201': '0201 (0603)',
	'0402': '0402 (1005)',
	'0603': '0603 (1608)',
	'0805': '0805 (2012)',
	'1206': '1206 (3216)',
	'1210': '1210 (3225)'
};

function sizeChoicesFor(availableSizes: readonly string[]): { id: string; label: string }[] {
	return availableSizes.map((id) => ({ id, label: EIA_CASE_SIZE_LABELS[id] ?? id }));
}

function commonOptions(availableSizes: readonly string[]): FamilyOption[] {
	const choices = sizeChoicesFor(availableSizes);
	return [
		{
			id: 'enabled_densities',
			label: 'Density variants',
			help: 'IPC-7351B density level suffix on the generated footprint name.',
			overridesGlobal: true,
			control: {
				kind: 'multiselect',
				choices: DENSITY_CHOICES,
				defaultValue: [...ALL_DENSITY_LEVELS]
			}
		},
		{
			id: 'sizes',
			label: 'Case sizes',
			help: 'EIA case sizes to include for this family.',
			overridesGlobal: true,
			control: {
				kind: 'multiselect',
				choices,
				defaultValue: choices.map((s) => s.id)
			}
		},
		{
			id: 'override_pad_radius',
			label: 'Pad corner radius (%)',
			help: 'Leave on Use global to inherit the project-wide setting.',
			overridesGlobal: true,
			control: { kind: 'number', defaultValue: 25, min: 0, max: 50, step: 1, unit: '%' }
		}
	];
}

// ---------------------------------------------------------------------------
// Catalog → runtime translation.
// ---------------------------------------------------------------------------

/** Convert a catalog control (snake_case wire format) to the runtime shape. */
function controlFromCatalog(c: FamilyOptionControlCatalog): FamilyOption['control'] {
	switch (c.kind) {
		case 'toggle':
			return { kind: 'toggle', defaultValue: c.default_value };
		case 'select':
			return { kind: 'select', choices: [...c.choices], defaultValue: c.default_value };
		case 'multiselect':
			return {
				kind: 'multiselect',
				choices: [...c.choices],
				defaultValue: [...c.default_value]
			};
		case 'number':
			return {
				kind: 'number',
				defaultValue: c.default_value,
				min: c.min,
				max: c.max,
				step: c.step,
				unit: c.unit
			};
		case 'text':
			return { kind: 'text', defaultValue: c.default_value, placeholder: c.placeholder };
	}
}

function optionFromCatalog(opt: FamilyOptionCatalog): FamilyOption {
	return {
		id: opt.id,
		label: opt.label,
		help: opt.help,
		overridesGlobal: opt.overrides_global,
		control: controlFromCatalog(opt.control)
	};
}

function familyFromCatalog(entry: FamilyCatalogEntry): FamilyDef {
	return {
		id: entry.id,
		name: entry.name,
		manufacturer: entry.manufacturer,
		summary: entry.summary,
		// Common options first (sized to this family's available_sizes), then
		// any family-specific extras. Most families don't have any extras.
		options: [...commonOptions(entry.available_sizes), ...entry.options.map(optionFromCatalog)]
	};
}

/**
 * Group flat catalog entries into the KindGroup → SubtypeGroup → FamilyDef
 * tree the Libraries tab renders. Order:
 *   - kinds in `KIND_ORDER`
 *   - within each kind, subtypes ordered by min(subtype_order) seen in
 *     entries with that subtype_id (ties broken by first-appearance)
 *   - within each subtype, families in catalog-emitted order (the Vite
 *     plugin already sorted by sort_order then id)
 *
 * Empty kinds (zero matching catalog entries) are dropped so the
 * Libraries-tab nav doesn't show blank tabs.
 */
function buildLibraryCatalog(): KindGroup[] {
	const groups: KindGroup[] = [];
	for (const kind of KIND_ORDER) {
		const ofKind = CATALOG_ENTRIES.filter((e) => e.kind === kind);
		if (ofKind.length === 0) continue;

		const subtypeMap = new Map<
			string,
			{ id: string; label: string; order: number; entries: FamilyCatalogEntry[] }
		>();
		for (const e of ofKind) {
			const cur = subtypeMap.get(e.subtype_id);
			if (cur) {
				if (e.subtype_order < cur.order) cur.order = e.subtype_order;
				cur.entries.push(e);
			} else {
				subtypeMap.set(e.subtype_id, {
					id: e.subtype_id,
					label: e.subtype_label,
					order: e.subtype_order,
					entries: [e]
				});
			}
		}

		const subtypes: SubtypeGroup[] = [...subtypeMap.values()]
			.sort((a, b) => a.order - b.order || a.id.localeCompare(b.id))
			.map((s) => ({
				id: s.id,
				label: s.label,
				families: s.entries.map(familyFromCatalog)
			}));

		groups.push({ id: kind, label: KIND_LABELS[kind], subtypes });
	}
	return groups;
}

export const LIBRARY_CATALOG: KindGroup[] = buildLibraryCatalog();

export function allFamilies(): FamilyDef[] {
	return LIBRARY_CATALOG.flatMap((k) => k.subtypes.flatMap((s) => s.families));
}
