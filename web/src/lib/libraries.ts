// Catalog of vendor component family libraries this project knows how to build.
// Drives the Libraries tab UI and the eventual Python-side build invocations.

export type ComponentKind = 'resistor' | 'capacitor' | 'ferrite' | 'inductor';

export interface FamilyOption {
	/** Stable id used as a key in app state. */
	id: string;
	/** Human-readable label. */
	label: string;
	/** Optional helper text under the input. */
	help?: string;
	/** Form control to render. */
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

const densityChoices = [
	{ id: 'L', label: 'L (Least)' },
	{ id: 'N', label: 'N (Nominal)' },
	{ id: 'M', label: 'M (Most)' }
];

const allDensities: string[] = ['L', 'N', 'M'];

const sizeChoices = [
	{ id: '01005', label: '01005 (0402 metric)' },
	{ id: '0201', label: '0201 (0603 metric)' },
	{ id: '0402', label: '0402 (1005 metric)' },
	{ id: '0603', label: '0603 (1608 metric)' },
	{ id: '0805', label: '0805 (2012 metric)' },
	{ id: '1206', label: '1206 (3216 metric)' },
	{ id: '1210', label: '1210 (3225 metric)' }
];

function commonOptions(): FamilyOption[] {
	return [
		{
			id: 'enabled_densities',
			label: 'Density variants to emit',
			help: 'IPC-7351B density level suffix on the generated footprint name.',
			control: { kind: 'multiselect', choices: densityChoices, defaultValue: allDensities }
		},
		{
			id: 'override_pad_radius',
			label: 'Pad corner radius (%)',
			help: 'Override HLCL global. Leave on Use global to inherit project setting.',
			overridesGlobal: true,
			control: { kind: 'number', defaultValue: 25, min: 0, max: 50, step: 1, unit: '%' }
		}
	];
}

export const LIBRARY_CATALOG: KindGroup[] = [
	{
		id: 'resistor',
		label: 'Resistors',
		subtypes: [
			{
				id: 'thick-film',
				label: 'Thick film',
				families: [
					{
						id: 'panasonic-erj',
						name: 'Panasonic ERJ',
						manufacturer: 'Panasonic',
						summary: 'General-purpose thick-film chip resistors, 01005–0805.',
						options: [
							...commonOptions(),
							{
								id: 'sizes',
								label: 'Case sizes',
								control: {
									kind: 'multiselect',
									choices: sizeChoices.filter((s) =>
										['01005', '0201', '0402', '0603', '0805'].includes(s.id)
									),
									defaultValue: ['01005', '0201', '0402', '0603', '0805']
								}
							}
						]
					}
				]
			},
			{
				id: 'thin-film',
				label: 'Thin film',
				families: [
					{
						id: 'panasonic-era-a',
						name: 'Panasonic ERA-A',
						manufacturer: 'Panasonic',
						summary: 'Thin-film high-precision, 0201 only.',
						options: commonOptions()
					},
					{
						id: 'panasonic-era-v',
						name: 'Panasonic ERA-V/K',
						manufacturer: 'Panasonic',
						summary: 'Thin-film high-stability, 0402–0805.',
						options: commonOptions()
					},
					{
						id: 'panasonic-era-p',
						name: 'Panasonic ERA-P',
						manufacturer: 'Panasonic',
						summary: 'Thin-film 500 V high-voltage, 1206 only.',
						options: commonOptions()
					}
				]
			},
			{
				id: 'metal-film',
				label: 'Metal film / current-sense',
				families: [
					{
						id: 'ohmite-kdv',
						name: 'Ohmite KDV',
						manufacturer: 'Ohmite',
						summary: 'Metal-film current-sense resistors.',
						options: commonOptions()
					}
				]
			}
		]
	},
	{
		id: 'capacitor',
		label: 'Capacitors',
		subtypes: [
			{
				id: 'mlcc-automotive',
				label: 'MLCC (automotive-qualified)',
				families: [
					{
						id: 'murata-gcm',
						name: 'Murata GCM',
						manufacturer: 'Murata',
						summary: 'Automotive AEC-Q200 MLCC capacitors.',
						options: [
							...commonOptions(),
							{
								id: 'min_voltage',
								label: 'Minimum voltage rating',
								help: 'Filter out parts rated below this voltage.',
								control: {
									kind: 'number',
									defaultValue: 6.3,
									min: 1,
									max: 1000,
									step: 0.1,
									unit: 'V'
								}
							}
						]
					},
					{
						id: 'tdk-capacitors',
						name: 'TDK CGA',
						manufacturer: 'TDK',
						summary: 'Automotive-qualified MLCC (CGA series).',
						options: commonOptions()
					}
				]
			},
			{
				id: 'mlcc-commercial',
				label: 'MLCC (commercial)',
				families: [
					{
						id: 'murata-grm',
						name: 'Murata GRM',
						manufacturer: 'Murata',
						summary: 'Commercial / general-purpose MLCC.',
						options: commonOptions()
					},
					{
						id: 'samsung-capacitors',
						name: 'Samsung CL',
						manufacturer: 'Samsung',
						summary: 'Commercial / general-purpose MLCC.',
						options: commonOptions()
					}
				]
			}
		]
	},
	{
		id: 'ferrite',
		label: 'Ferrite beads',
		subtypes: [
			{
				id: 'chip-ferrite',
				label: 'Chip ferrite beads',
				families: [
					{
						id: 'murata-ferrites',
						name: 'Murata BLM',
						manufacturer: 'Murata',
						summary: 'BLM-series chip ferrite beads.',
						options: commonOptions()
					}
				]
			}
		]
	},
	{
		id: 'inductor',
		label: 'Inductors',
		subtypes: [
			{
				id: 'chip-inductor',
				label: 'Chip inductors',
				families: []
			}
		]
	}
];

export function allFamilies(): FamilyDef[] {
	return LIBRARY_CATALOG.flatMap((k) => k.subtypes.flatMap((s) => s.families));
}
