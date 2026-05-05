/**
 * Pure helpers for the Preview tab. None of these touch the DOM or `$state`
 * directly — they accept plain snapshots from `appState.snapshot()` so the
 * tab can re-derive everything reactively.
 *
 *   - `serializeSettingsToml(project)` produces a `house/settings.toml`-style
 *     dump of the current project settings so the user can sanity-check it
 *     against the real file.
 *   - `computeBuildPlan(state)` turns the build flags + enabled families into
 *     an ordered list of build steps the in-browser pipeline will run, with
 *     the matching `python build.py <target>` name on each row for traceability.
 *   - `summarizeFamilyOverrides(state)` walks the per-family options and
 *     surfaces just the ones that are actively overriding the global default.
 */

import type {
	BuildSettings,
	FamilyOptionValue,
	FamilyState,
	PersistedState,
	ProjectSettings
} from './state.svelte';
import { allFamilies, type FamilyDef } from './libraries';

// ---------------------------------------------------------------------------
// TOML serializer
// ---------------------------------------------------------------------------

function tomlString(s: string): string {
	// Basic-string with the four characters TOML §7 requires we escape.
	return `"${s.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\n/g, '\\n').replace(/\r/g, '\\r')}"`;
}

function tomlNumber(n: number): string {
	if (Number.isInteger(n)) return n.toString();
	// Keep at least one fractional digit so floats round-trip as floats.
	return Number.isFinite(n) ? n.toString() : 'nan';
}

function tomlInline(value: unknown): string {
	if (typeof value === 'string') return tomlString(value);
	if (typeof value === 'number') return tomlNumber(value);
	if (typeof value === 'boolean') return value ? 'true' : 'false';
	if (Array.isArray(value)) {
		const parts = value.map((v) => tomlInline(v));
		// Multi-line arrays once we exceed ~5 entries or the line gets unwieldy.
		const inline = `[${parts.join(', ')}]`;
		if (parts.length <= 5 && inline.length <= 72) return inline;
		return `[\n${parts.map((p) => `    ${p},`).join('\n')}\n]`;
	}
	if (value === null || value === undefined) return '""';
	return tomlString(String(value));
}

interface TomlTable {
	scalars: Record<string, unknown>;
	tables: Record<string, TomlTable>;
}

function emptyTable(): TomlTable {
	return { scalars: {}, tables: {} };
}

function toTable(obj: Record<string, unknown>): TomlTable {
	const out = emptyTable();
	for (const [k, v] of Object.entries(obj)) {
		if (
			v !== null &&
			typeof v === 'object' &&
			!Array.isArray(v) &&
			Object.keys(v as object).length > 0
		) {
			out.tables[k] = toTable(v as Record<string, unknown>);
		} else {
			out.scalars[k] = v;
		}
	}
	return out;
}

function emitTable(table: TomlTable, path: string[]): string {
	const lines: string[] = [];
	if (path.length > 0 && Object.keys(table.scalars).length > 0) {
		lines.push(`[${path.join('.')}]`);
	}
	for (const [k, v] of Object.entries(table.scalars)) {
		lines.push(`${k} = ${tomlInline(v)}`);
	}
	for (const [k, sub] of Object.entries(table.tables)) {
		const subPath = [...path, k];
		if (lines.length > 0) lines.push('');
		const subBody = emitTable(sub, subPath);
		// emitTable writes its own header for non-empty tables.
		if (!subBody.startsWith('[')) {
			lines.push(`[${subPath.join('.')}]`);
		}
		lines.push(subBody);
	}
	return lines.join('\n');
}

export function serializeSettingsToml(project: ProjectSettings): string {
	// Match the file ordering of `house/settings.toml` so a side-by-side diff
	// against the repo's checked-in version reads naturally.
	const tree = emptyTable();
	tree.tables.house_footprints = toTable({ priority: project.priority });
	tree.tables.ipc = toTable(project.ipc as unknown as Record<string, unknown>);
	tree.tables.hlcl = toTable(project.hlcl as unknown as Record<string, unknown>);
	tree.tables.stepgen = toTable(project.stepgen as unknown as Record<string, unknown>);

	// `colors.*` are nested tables; emit each sub-table by hand so the order
	// matches the canonical settings.toml layout.
	const colorRoot = emptyTable();
	for (const [name, palette] of Object.entries(project.colors)) {
		colorRoot.tables[name] = toTable(palette as unknown as Record<string, unknown>);
	}
	tree.tables.colors = colorRoot;

	const header = [
		'# HLCL configurator preview — `house/settings.toml`.',
		'# Mirrors the file in the repo at this path:',
		'#   house/settings.toml',
		'# Loaded by stdlib `tomllib` (Python >= 3.11).',
		''
	].join('\n');

	return header + emitTable(tree, []);
}

// ---------------------------------------------------------------------------
// Build plan
// ---------------------------------------------------------------------------

export interface BuildStep {
	id: string;
	target: string; // `python build.py <target>` name
	title: string;
	detail: string;
	outputs: string[];
	stage: 'vendor' | 'merge' | 'step' | 'pcblib' | 'schlib' | 'standards' | 'package';
}

const FAMILY_BASENAME: Record<string, string> = {
	'panasonic-erj': 'panasonic-erj',
	'panasonic-era-a': 'panasonic-era-a',
	'panasonic-era-v': 'panasonic-era-v',
	'panasonic-era-p': 'panasonic-era-p',
	'ohmite-kdv': 'ohmite-kdv',
	'samsung-capacitors': 'samsung-capacitors',
	'tdk-capacitors': 'tdk-capacitors',
	'murata-gcm': 'murata-gcm',
	'murata-grm': 'murata-grm',
	// Make target is plural; the file basename is singular (legacy quirk).
	'murata-ferrites': 'murata-ferrite'
};

function vendorBasename(targetId: string): string {
	return FAMILY_BASENAME[targetId] ?? targetId;
}

export function computeBuildPlan(state: PersistedState): BuildStep[] {
	const enabled = Object.entries(state.families)
		.filter(([, v]) => v.enabled)
		.map(([id]) => id);
	const steps: BuildStep[] = [];
	const b: BuildSettings = state.build;

	if (b.emit_xls || b.emit_dblib || b.emit_footprints_json) {
		for (const id of enabled) {
			const base = vendorBasename(id);
			const outputs: string[] = [];
			if (b.emit_xls) outputs.push(`build/output/${base}.xls`);
			if (b.emit_dblib) outputs.push(`build/output/${base}.DbLib`);
			if (b.emit_footprints_json)
				outputs.push(`build/intermediate/footprints/${base}-footprints.json`);
			steps.push({
				id: `vendor-${id}`,
				target: id,
				title: `Build ${id}`,
				detail: `Run vendors/.../${base}.py to emit the family's database + footprints.`,
				outputs,
				stage: 'vendor'
			});
		}
	}

	if (b.emit_house_footprints_merge && enabled.length > 0) {
		steps.push({
			id: 'house-footprints',
			target: 'house-footprints',
			title: 'Merge per-vendor footprints',
			detail:
				'house/build_house_footprints.py merges every vendor JSON, breaking ties using the project priority list.',
			outputs: ['build/intermediate/footprints/house-footprints.json'],
			stage: 'merge'
		});
	}

	if (b.emit_step_models && enabled.length > 0) {
		steps.push({
			id: 'house-step-models',
			target: 'house-step-models',
			title: 'Generate parametric STEP 3D models',
			detail:
				'house/build_step_models.py emits one STEP per unique chip body (deduped by footprint root).',
			outputs: ['build/intermediate/step/*.step'],
			stage: 'step'
		});
	}

	if (b.emit_pcblib && enabled.length > 0) {
		steps.push({
			id: 'house-pcblib',
			target: 'house-pcblib',
			title: 'Build house.PcbLib',
			detail:
				'house/build_pcblib.py applies IPC-7351B pad math + HLCL-001 standards and zlib-embeds each STEP.',
			outputs: ['build/output/house.PcbLib'],
			stage: 'pcblib'
		});
	}

	if (b.emit_schlib) {
		steps.push({
			id: 'house-schlib',
			target: 'house-schlib',
			title: 'Stage house.SchLib',
			detail: 'Copy the hand-maintained schematic library next to the .DbLib outputs.',
			outputs: ['build/output/house.SchLib'],
			stage: 'schlib'
		});
	}

	if (b.emit_standards_pdf) {
		steps.push({
			id: 'standards',
			target: 'standards',
			title: 'Typeset HLCL-001 standards PDF',
			detail: 'Two-pass pdflatex of docs/standards/HLCL-001.tex.',
			outputs: ['build/output/standards/HLCL-001.pdf'],
			stage: 'standards'
		});
	}

	if (b.zip_output && steps.length > 0) {
		steps.push({
			id: 'zip',
			target: '(in-browser)',
			title: 'Bundle into hlcl-build.zip',
			detail: 'Pack every produced artifact into a single download for convenience.',
			outputs: ['hlcl-build.zip'],
			stage: 'package'
		});
	}

	return steps;
}

// ---------------------------------------------------------------------------
// Family overrides summary
// ---------------------------------------------------------------------------

export interface FamilyOverrideSummary {
	id: string;
	def: FamilyDef;
	state: FamilyState;
	overriddenOptions: { id: string; label: string; value: FamilyOptionValue }[];
}

export function summarizeEnabledFamilies(state: PersistedState): FamilyOverrideSummary[] {
	const defs = allFamilies();
	const out: FamilyOverrideSummary[] = [];
	for (const def of defs) {
		const fam = state.families[def.id];
		if (!fam || !fam.enabled) continue;
		const overriddenOptions: FamilyOverrideSummary['overriddenOptions'] = [];
		for (const opt of def.options) {
			if (opt.overridesGlobal && fam.overrides?.[opt.id]) {
				overriddenOptions.push({ id: opt.id, label: opt.label, value: fam.options[opt.id] });
			} else if (!opt.overridesGlobal && opt.control.kind === 'multiselect') {
				const cur = fam.options[opt.id];
				const def_ = opt.control.defaultValue;
				if (
					Array.isArray(cur) &&
					(cur.length !== def_.length || cur.some((v, i) => v !== def_[i]))
				) {
					overriddenOptions.push({ id: opt.id, label: opt.label, value: cur });
				}
			}
		}
		out.push({ id: def.id, def, state: fam, overriddenOptions });
	}
	return out;
}

export function formatOptionValue(v: FamilyOptionValue): string {
	if (Array.isArray(v)) return v.length === 0 ? '∅' : v.join(', ');
	if (typeof v === 'boolean') return v ? 'on' : 'off';
	return String(v);
}
