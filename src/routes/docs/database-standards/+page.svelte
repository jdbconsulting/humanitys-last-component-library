<script lang="ts">
	type Row = readonly [string, string];

	const generalRules: Row[] = [
		['Descriptions', 'ALL CAPS, one line, no trailing period.'],
		['Parameter fields', 'Mixed case is allowed, for example 10nF or +/-15%.'],
		['SI prefixes', 'p, n, u, m, k, M. Write u, never µ.'],
		['Units', 'OHM in descriptions; V, A, W, Hz, F and H everywhere.'],
		[
			'Tolerance',
			'Absolute tolerances carry a unit (+/-0.25pF). Percentages use % (5%). Never write ±.'
		],
		['Temperature range', 'Minimum and maximum separated by a colon, for example -55:125.'],
		['Voltage', 'Always includes the V suffix, for example 25V or 6.3V.'],
		['Character set', 'ASCII only, in every database field.']
	];

	const descriptionFormats = [
		{
			kind: 'Resistors',
			format: 'RESISTOR {CONSTRUCTION} {VALUE} OHM {TOLERANCE} {EIA_SIZE}',
			examples: ['RESISTOR THICK FILM 10K OHM 1% 0402', 'RESISTOR JUMPER 0 OHM 0402'],
			note: 'Jumpers use RESISTOR JUMPER 0 OHM {EIA_SIZE}. CONSTRUCTION is the film or element type, such as THICK FILM or THIN FILM.',
			values: [
				['Below 1 kΩ', 'Plain number: 100, 4.7'],
				['1 kΩ to below 1 MΩ', 'K suffix: 1K, 47K, 4.7K'],
				['1 MΩ and above', 'M suffix: 1M, 2.2M']
			] as Row[]
		},
		{
			kind: 'Capacitors',
			format: 'CAPACITOR CERAMIC {VALUE} {TOLERANCE} {VOLTAGE} {DIELECTRIC} {EIA_SIZE}',
			examples: ['CAPACITOR CERAMIC 100NF 10% 16V X7R 0402'],
			note: '',
			values: [
				['Below 1 nF', 'PF: 100PF, 4.7PF'],
				['1 nF to below 1 µF', 'NF: 10NF, 470NF'],
				['1 µF and above', 'UF: 1UF, 100UF']
			] as Row[]
		},
		{
			kind: 'Inductors',
			format: 'INDUCTOR {CONSTRUCTION} {VALUE} {TOLERANCE} {DCR} {EIA_SIZE}',
			examples: ['INDUCTOR MULTILAYER 4.7UH 20% 0.1 OHM 0402'],
			note: 'Inductance uses an upper-case unit suffix: NH, UH or MH (100NH, 4.7UH, 10MH).',
			values: [] as Row[]
		},
		{
			kind: 'Ferrite beads',
			format: 'FERRITE BEAD {IMPEDANCE} {RATED_CURRENT} {EIA_SIZE}',
			examples: ['FERRITE BEAD 60 OHM 1A 0402'],
			note: 'IMPEDANCE is the typical impedance at 100 MHz, with the OHM unit (120 OHM, 1K OHM).',
			values: [] as Row[]
		}
	];

	const commonFields: Row[] = [
		['Comment', 'Full MPN. The unique key the database library binds to.'],
		['Description', 'Per the description format above.'],
		['MFG', 'Manufacturer name, ALL CAPS.'],
		['MPN', 'Same as Comment.'],
		['Package', 'Imperial (inch) package name, ALL CAPS, for example 0402.'],
		['Library Path', 'Schematic library filename.'],
		['Library Ref', 'Symbol name, for example RES or CAP.'],
		['Footprint Path', 'PCB library filename.'],
		['Footprint Ref', 'Footprint name, nominal material condition (N).'],
		['Footprint Path 2', 'PCB library filename (same).'],
		['Footprint Ref 2', 'Footprint name, least material condition (L).'],
		['Footprint Path 3', 'PCB library filename (same).'],
		['Footprint Ref 3', 'Footprint name, most material condition (M).'],
		['Qual', 'Qualification, for example AEC-Q200. Blank if none.']
	];

	const typeFields: { kind: string; rows: Row[] }[] = [
		{
			kind: 'Resistors',
			rows: [
				['Value', 'Resistance as {number}{prefix}, without OHM: 100, 4.7k, 1M. Jumpers: 0.'],
				['Tolerance', 'Value tolerance: 5%, 0.1%.'],
				['Voltage', 'Limiting element voltage: 50V.'],
				['Tcr', 'Temperature coefficient: +/-100. ppm/K is implied.'],
				['Tr', 'Operating temperature range: -55:155.']
			]
		},
		{
			kind: 'Capacitors',
			rows: [
				['Value', 'Capacitance as {number}{prefix}F: 100pF, 4.7nF, 10uF.'],
				['Tolerance', 'Value tolerance: 5%, +/-0.25pF.'],
				['Voltage', 'Rated DC voltage: 25V.'],
				['Tcr', 'Temperature characteristic: +/-15%, +/-30.'],
				['Tr', 'Operating temperature range: -55:125.']
			]
		},
		{
			kind: 'Inductors',
			rows: [
				['Value', 'Inductance as {number}{prefix}H: 100uH, 4.7uH, 10mH.'],
				['Tolerance', 'Value tolerance: 5%, 20%.'],
				['DCR', 'DC resistance: 0.1, 2.1m. Ohms are implied.'],
				['Current', 'Rated RMS current or Isat, as applicable: 1.5A.'],
				['Tr', 'Operating temperature range: -40:85.']
			]
		},
		{
			kind: 'Ferrite beads',
			rows: [
				[
					'Value',
					'Impedance at 100 MHz with OHM: 60OHM, 1KOHM. State the frequency if the datasheet uses another.'
				],
				['Current', 'Rated RMS current: 1A, 2A.'],
				['DCR', 'DC resistance: 0.1, 2.1m. Ohms are implied.'],
				['Tr', 'Operating temperature range: -40:85.']
			]
		}
	];

	const exampleRow: Row[] = [
		['Comment', 'CRCW06034K70JNEA'],
		['Description', 'RESISTOR THICK FILM 4.7K OHM 5% 0603'],
		['MFG', 'VISHAY'],
		['MPN', 'CRCW06034K70JNEA'],
		['Package', '0603'],
		['Library Path', 'house.SchLib'],
		['Library Ref', 'RES'],
		['Footprint Path / Ref', 'house.PcbLib / RESC1608X50_CRCWN'],
		['Footprint Path 2 / Ref 2', 'house.PcbLib / RESC1608X50_CRCWL'],
		['Footprint Path 3 / Ref 3', 'house.PcbLib / RESC1608X50_CRCWM'],
		['Qual', 'AEC-Q200'],
		['Value', '4.7k'],
		['Tolerance', '5%'],
		['Voltage', '75V'],
		['Tcr', '+/-200'],
		['Tr', '-55:155']
	];

	const th = 'px-4 py-2 text-left';
	const td = 'px-4 py-2 align-top';
</script>

<svelte:head>
	<title>Database standards · Docs · HLCL</title>
</svelte:head>

{#snippet fieldTable(rows: Row[], left: string, right: string)}
	<div class="overflow-x-auto rounded-lg border border-ink-200">
		<table class="min-w-full divide-y divide-ink-200 text-sm">
			<thead class="bg-ink-50 text-[11px] font-semibold tracking-wider text-ink-500 uppercase">
				<tr><th class={th}>{left}</th><th class={th}>{right}</th></tr>
			</thead>
			<tbody class="divide-y divide-ink-100">
				{#each rows as [name, content] (name)}
					<tr>
						<td class="{td} font-mono text-xs whitespace-nowrap text-ink-900">{name}</td>
						<td class="{td} text-ink-700">{content}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/snippet}

<h1 class="text-3xl font-bold tracking-tight text-ink-900">Database standards</h1>

<div class="prose-docs mt-8 space-y-5 text-ink-700">
	<p>
		These conventions govern the descriptions, parameter values and columns in the generated
		<code class="font-mono text-sm">.xls</code> database workbooks. Following them keeps parts searchable,
		sortable and consistent across manufacturers, whichever family a part comes from.
	</p>
	<p>
		Every family's workbook follows this standard. The build rejects any row whose description is
		not all caps, ends with a period or starts with the wrong component prefix, whose value,
		tolerance, voltage, Tcr, temperature range, DCR or current is malformed, or that contains a
		non-ASCII character in any field. Use the workbook viewer on the Generate tab to check columns
		before you download.
	</p>

	<h2 class="pt-4 text-xl font-semibold text-ink-900">General rules</h2>
	{@render fieldTable(generalRules, 'Rule', 'Convention')}

	<h2 class="pt-4 text-xl font-semibold text-ink-900">Description format</h2>
	<p>
		Descriptions are one line, ALL CAPS and space-delimited, with fields in the order defined for
		each component type.
	</p>
	{#each descriptionFormats as d (d.kind)}
		<h3 class="pt-2 text-base font-semibold text-ink-900">{d.kind}</h3>
		<pre
			class="overflow-x-auto rounded-md bg-ink-50 px-4 py-3 font-mono text-xs text-ink-900 ring-1 ring-ink-200">{d.format}</pre>
		<p class="text-sm">
			Example{d.examples.length > 1 ? 's' : ''}:
			{#each d.examples as example, i (example)}
				<code class="font-mono text-xs text-ink-900">{example}</code>{i < d.examples.length - 1
					? ' · '
					: ''}
			{/each}
		</p>
		{#if d.note}
			<p class="text-sm">{d.note}</p>
		{/if}
		{#if d.values.length}
			{@render fieldTable(d.values, 'Range', 'Value notation in descriptions')}
		{/if}
	{/each}

	<h2 class="pt-4 text-xl font-semibold text-ink-900">Database fields</h2>
	<p>
		Every workbook lists the common fields first, then the fields for its component type. By default
		it contains no other columns. Some families can add extra, non-standard columns, such as Power,
		Datasheet, alternate MPNs, SRF or Q: tick them under <em>Extra / non-standard parameters</em> on the
		family's card in the Libraries tab. Extra columns follow the standard ones and obey the same general
		rules. Alternate MPN columns (MFG 2 / MPN 2 to MFG 5 / MPN 5) are written only as far as some part
		in the workbook has an alternate to list.
	</p>
	<h3 class="pt-2 text-base font-semibold text-ink-900">Common fields (all types)</h3>
	{@render fieldTable(commonFields, 'Column', 'Content')}
	{#each typeFields as t (t.kind)}
		<h3 class="pt-2 text-base font-semibold text-ink-900">{t.kind}</h3>
		{@render fieldTable(t.rows, 'Column', 'Content')}
	{/each}

	<h2 class="pt-4 text-xl font-semibold text-ink-900">Example row</h2>
	<p>A Vishay CRCW 0603 resistor, 4.7 kΩ, 5%, as it appears in the generated workbook:</p>
	{@render fieldTable(exampleRow, 'Column', 'Value')}
</div>
