/**
 * Named configuration presets. Each preset is a partial `PresetDelta` that
 * `AppState.applyPreset()` overlays on top of factory defaults.
 *
 * Adding a preset
 * ---------------
 * 1. Pick a stable id — used in localStorage so renaming is breaking.
 * 2. Fill in the fields you want the preset to dictate. Anything left out
 *    inherits the factory default.
 * 3. The `summary` and `bullets` fields drive the card UI; keep them short.
 */

import type { PresetDelta } from './state.svelte';
import { allFamilies } from './libraries';

export interface Preset {
	id: string;
	name: string;
	tagline: string;
	summary: string;
	icon: 'reset' | 'consumer' | 'automotive' | 'precision' | 'voltage' | 'all';
	bullets: string[];
	delta: PresetDelta;
}

const ALL_FAMILY_IDS = allFamilies().map((f) => f.id);

export const PRESETS: Preset[] = [
	{
		id: 'defaults',
		name: 'Factory defaults',
		tagline: 'Reset',
		icon: 'reset',
		summary:
			"Starting point. Three popular families enabled, IPC-7351B's worked-example tolerances, every artifact emitted.",
		bullets: [
			'Panasonic ERJ + Samsung CL + Murata BLM enabled',
			'F = 0.10 mm, P = 0.05 mm (IPC-7351B §3.1.4 example)',
			'HLCL-001 drawing standards as published',
			'Standards PDF off (heavy LaTeX dep), everything else on'
		],
		delta: {
			families: ['panasonic-erj', 'samsung-capacitors', 'murata-ferrites']
		}
	},
	{
		id: 'consumer',
		name: 'Consumer / commercial',
		tagline: 'Cost-optimised',
		icon: 'consumer',
		summary:
			'Mainstream commercial passives at the lowest BOM cost. Loose-but-IPC-compliant pad math; full density-variant set so the routing engineer keeps options.',
		bullets: [
			'Panasonic ERJ (thick film), Samsung CL + Murata GRM (commercial MLCC)',
			'Murata BLM ferrites',
			'Default IPC tolerances; HLCL standards unchanged',
			'.PcbLib + .DbLib + STEP, no standards PDF'
		],
		delta: {
			families: ['panasonic-erj', 'samsung-capacitors', 'murata-grm', 'murata-ferrites'],
			project: {
				ipc: { fabrication_tolerance_mm: 0.1, placement_tolerance_mm: 0.05 }
			}
		}
	},
	{
		id: 'automotive',
		name: 'Automotive · AEC-Q200',
		tagline: 'AEC-Q200 / Q101',
		icon: 'automotive',
		summary:
			'Automotive-qualified passives only — Murata GCM, TDK CGA. Tighter F/P tolerances reflecting a pre-qualified assembly line. Density variant N picked across the board.',
		bullets: [
			'Murata GCM + TDK CGA (automotive MLCC)',
			'Panasonic ERJ (thick film, AEC-Q200 grade)',
			'F = 0.075 mm, P = 0.035 mm (qualified placement)',
			'Solder-mask sliver bumped to 0.12 mm for AEC pads'
		],
		delta: {
			families: ['panasonic-erj', 'murata-gcm', 'tdk-capacitors', 'murata-ferrites'],
			familyOptions: {
				'murata-gcm': { enabled_densities: ['N'], min_voltage: 16 },
				'tdk-capacitors': { enabled_densities: ['N'] },
				'panasonic-erj': { enabled_densities: ['N'] }
			},
			project: {
				ipc: { fabrication_tolerance_mm: 0.075, placement_tolerance_mm: 0.035 },
				hlcl: { min_solder_mask_sliver_mm: 0.12 },
				priority: [
					'panasonic-erj',
					'murata-gcm',
					'tdk-capacitors',
					'murata-ferrite',
					'samsung-capacitors',
					'murata-grm',
					'ohmite-kdv',
					'panasonic-era-a',
					'panasonic-era-v',
					'panasonic-era-p'
				]
			}
		}
	},
	{
		id: 'precision',
		name: 'High-precision thin-film',
		tagline: 'Lab / metrology',
		icon: 'precision',
		summary:
			'Thin-film resistors across the Panasonic ERA-A/V/P range plus automotive MLCC for the supporting capacitors. All density variants emitted — pick per board rule.',
		bullets: [
			'Panasonic ERA-A (0201), ERA-V/K (0402–0805), ERA-P (1206)',
			'Murata GCM + TDK CGA capacitors (low-noise grade)',
			'F = 0.07 mm, P = 0.03 mm (precision placement)',
			'Pad corner radius 30%, mask expansion 0.04 mm'
		],
		delta: {
			families: [
				'panasonic-era-a',
				'panasonic-era-v',
				'panasonic-era-p',
				'murata-gcm',
				'tdk-capacitors'
			],
			project: {
				ipc: { fabrication_tolerance_mm: 0.07, placement_tolerance_mm: 0.03 },
				hlcl: {
					pad_corner_radius_percent: 30,
					solder_mask_expansion_mm: 0.04,
					min_solder_mask_sliver_mm: 0.1
				}
			}
		}
	},
	{
		id: 'highvoltage',
		name: 'High-voltage / power',
		tagline: 'High V, sense',
		icon: 'voltage',
		summary:
			'High-voltage thin-film + current-sense focus. ERA-P 500 V resistors, Ohmite KDV current-sense, Murata GCM for high-V class capacitors.',
		bullets: [
			'Panasonic ERA-P (1206 thin-film, 500 V)',
			'Ohmite KDV current-sense resistors',
			'Murata GCM (X7R / NP0 high-V parts)',
			'Default IPC tolerances; mask sliver 0.15 mm for HV creepage'
		],
		delta: {
			families: ['panasonic-era-p', 'ohmite-kdv', 'murata-gcm'],
			familyOptions: {
				'murata-gcm': { min_voltage: 50 }
			},
			project: {
				hlcl: { min_solder_mask_sliver_mm: 0.15 }
			}
		}
	},
	{
		id: 'everything',
		name: 'Everything · the kitchen sink',
		tagline: 'All families',
		icon: 'all',
		summary:
			'Every vendor family this build chain knows about, every density variant, every artifact (including the standards PDF). Slowest preset to build; biggest output set.',
		bullets: [
			`All ${ALL_FAMILY_IDS.length} family generators turned on`,
			'L / N / M density variants emitted everywhere',
			'Standards PDF + house.SchLib + house.PcbLib all packaged',
			'Useful as a regression baseline'
		],
		delta: {
			families: ALL_FAMILY_IDS,
			build: {
				emit_xls: true,
				emit_dblib: true,
				emit_footprints_json: true,
				emit_house_footprints_merge: true,
				emit_step_models: true,
				emit_pcblib: true,
				emit_schlib: true,
				emit_standards_pdf: true,
				zip_output: true
			}
		}
	}
];

export function getPreset(id: string): Preset | undefined {
	return PRESETS.find((p) => p.id === id);
}
