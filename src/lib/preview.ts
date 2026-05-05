/**
 * Pure helpers for the Preview tab. None of these touch the DOM or `$state`
 * directly — they accept plain `BuildConfig` snapshots so the tab can
 * re-derive everything reactively.
 *
 *   - `computeBuildPlan(config)` turns the artifact flags + enabled families
 *     into an ordered list of build steps the in-browser pipeline will run,
 *     with the matching `python build.py <target>` name on each row for
 *     traceability.
 *   - `summarizeEnabledFamilies(config)` walks the per-family options and
 *     surfaces just the ones that are actively overriding the global default.
 */

import type { Artifacts, BuildConfig, FamilyConfig, FamilyOptionValue } from './schema';
import { allFamilies, type FamilyDef } from './libraries';

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

export function computeBuildPlan(config: BuildConfig): BuildStep[] {
	const enabled = Object.entries(config.families)
		.filter(([, v]) => v.enabled)
		.map(([id]) => id);
	const steps: BuildStep[] = [];
	const a: Artifacts = config.artifacts;

	if (a.xls || a.dblib || a.footprints_json) {
		for (const id of enabled) {
			const base = vendorBasename(id);
			const outputs: string[] = [];
			if (a.xls) outputs.push(`build/output/${base}.xls`);
			if (a.dblib) outputs.push(`build/output/${base}.DbLib`);
			if (a.footprints_json) outputs.push(`build/intermediate/footprints/${base}-footprints.json`);
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

	if (a.house_footprints_merge && enabled.length > 0) {
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

	if (a.step_models && enabled.length > 0) {
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

	if (a.pcblib && enabled.length > 0) {
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

	if (a.schlib) {
		steps.push({
			id: 'house-schlib',
			target: 'house-schlib',
			title: 'Stage house.SchLib',
			detail: 'Copy the hand-maintained schematic library next to the .DbLib outputs.',
			outputs: ['build/output/house.SchLib'],
			stage: 'schlib'
		});
	}

	if (a.standards_tex || a.standards_md) {
		const outputs: string[] = [];
		const formats: string[] = [];
		if (a.standards_tex) {
			outputs.push('build/output/standards/standards.tex');
			formats.push('LaTeX');
		}
		if (a.standards_md) {
			outputs.push('build/output/standards/standards.md');
			formats.push('Markdown');
		}
		// The reference figures are always copied alongside whichever
		// rendering(s) are produced so the file is self-contained.
		outputs.push('build/output/standards/example-symbol.png');
		outputs.push('build/output/standards/example-footprint.png');
		steps.push({
			id: 'standards',
			target: 'standards',
			title: `Render HLCL-001 standards (${formats.join(' + ')})`,
			detail:
				'Substitute the active drawing-standard values into docs/standards/standards.{tex,md} and stage the populated copies for download.',
			outputs,
			stage: 'standards'
		});
	}

	if (a.zip_output && steps.length > 0) {
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
	state: FamilyConfig;
	overriddenOptions: { id: string; label: string; value: FamilyOptionValue }[];
}

export function summarizeEnabledFamilies(config: BuildConfig): FamilyOverrideSummary[] {
	const defs = allFamilies();
	const out: FamilyOverrideSummary[] = [];
	for (const def of defs) {
		const fam = config.families[def.id];
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
