<script lang="ts">
	import { appState } from '$lib/state.svelte';
	import type { Artifacts } from '$lib/schema';
	import SectionHeader from '../SectionHeader.svelte';
	import Toggle from '../Toggle.svelte';

	interface BuildOption {
		key: keyof Artifacts;
		label: string;
		description: string;
		buildTarget?: string;
		group: 'vendor' | 'house' | 'standards' | 'package';
		recommended?: boolean;
	}

	const options: BuildOption[] = [
		{
			key: 'xls',
			label: 'Vendor .xls databases',
			description:
				'Excel 97-2003 BIFF8 workbook per vendor family — the table the .DbLib binds to in Altium.',
			buildTarget: 'panasonic-erj, samsung-capacitors, …',
			group: 'vendor',
			recommended: true
		},
		{
			key: 'dblib',
			label: 'Vendor .DbLib files',
			description: 'Altium DbLib pointing at the matching vendor .xls. Sibling LibrarySearchPath=.',
			buildTarget: 'auto-emitted alongside .xls',
			group: 'vendor',
			recommended: true
		},
		{
			key: 'footprints_json',
			label: 'Per-vendor footprints JSON',
			description:
				'Spec of unique CAPC/RESC/INDC × density variants the .xls references. Schema in vendors/_common.py.',
			group: 'vendor'
		},
		{
			key: 'house_footprints_merge',
			label: 'Merged house-footprints.json',
			description:
				'Tie-break-resolved merge of every vendor JSON via house/build_house_footprints.py.',
			buildTarget: 'house-footprints',
			group: 'house',
			recommended: true
		},
		{
			key: 'step_models',
			label: 'Parametric STEP 3D models',
			description:
				'Pure-stdlib generator (house/stepgen) emits one STEP per unique chip body. Required by .PcbLib embedding.',
			buildTarget: 'house-step-models',
			group: 'house',
			recommended: true
		},
		{
			key: 'pcblib',
			label: 'house.PcbLib',
			description:
				'AltiumSharp v1.0.2-compatible writer (house/altium_pcblib). Embeds STEP via zlib, applies HLCL-001.',
			buildTarget: 'house-pcblib',
			group: 'house',
			recommended: true
		},
		{
			key: 'schlib',
			label: 'house.SchLib',
			description: 'Hand-maintained schematic library copied alongside the .DbLib outputs.',
			buildTarget: 'house-schlib',
			group: 'house'
		},
		{
			key: 'standards_tex',
			label: 'standards.tex (LaTeX source)',
			description:
				'Populate docs/standards/standards.tex with the active drawing-standard values and include the rendered .tex in the build output. Compile to PDF yourself with pdflatex if you want a typeset copy.',
			buildTarget: 'standards',
			group: 'standards'
		},
		{
			key: 'standards_md',
			label: 'standards.md (Markdown)',
			description:
				'Same template-fill, rendered into a Markdown sibling. Renders in any Git host preview pane and ships next to your library for downstream readers.',
			buildTarget: 'standards',
			group: 'standards'
		},
		{
			key: 'zip_output',
			label: 'Bundle into a single .zip',
			description:
				'Produce a single download containing everything you ticked above. Disable to download files individually.',
			group: 'package',
			recommended: true
		}
	];

	const groups = [
		{ id: 'vendor' as const, label: 'Per-vendor outputs' },
		{ id: 'house' as const, label: 'Aggregated house artifacts' },
		{ id: 'standards' as const, label: 'HLCL-001 standards document' },
		{ id: 'package' as const, label: 'Packaging' }
	];
</script>

<SectionHeader
	title="Build settings"
	description="Pick which artifacts the in-browser build should emit. The pipeline lives in build.py at the repo root and runs entirely in Pyodide via build.build_target(...) — no subprocess, no make."
/>

<div class="mt-6 space-y-8">
	{#each groups as group (group.id)}
		<section>
			<h3 class="text-sm font-semibold tracking-wider text-navy-700 uppercase">{group.label}</h3>
			<div class="mt-3 grid gap-3 md:grid-cols-2">
				{#each options.filter((o) => o.group === group.id) as opt (opt.key)}
					<label
						class={[
							'flex cursor-pointer flex-col rounded-lg border bg-white p-4 transition',
							appState.config.artifacts[opt.key]
								? 'border-navy-300 bg-navy-50/40 ring-1 ring-navy-200'
								: 'border-ink-200 hover:border-ink-300'
						]}
					>
						<div class="flex items-start justify-between gap-3">
							<div>
								<div class="flex items-center gap-2">
									<span class="text-sm font-semibold text-ink-900">{opt.label}</span>
									{#if opt.recommended}
										<span
											class="rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700"
											>Recommended</span
										>
									{/if}
								</div>
								<p class="mt-1 text-xs text-ink-600">{opt.description}</p>
								{#if opt.buildTarget}
									<p class="mt-1 font-mono text-[10px] text-ink-500">
										python build.py {opt.buildTarget}
									</p>
								{/if}
							</div>
							<Toggle bind:checked={appState.config.artifacts[opt.key]} label="" />
						</div>
					</label>
				{/each}
			</div>
		</section>
	{/each}
</div>
