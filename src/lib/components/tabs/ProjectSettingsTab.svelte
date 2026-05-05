<script lang="ts">
	import { EIA_CASE_SIZE_LABELS } from '$lib/libraries';
	import { appState } from '$lib/state.svelte';
	import NumberField from '../NumberField.svelte';
	import SectionHeader from '../SectionHeader.svelte';
	function rgbToHex([r, g, b]: [number, number, number]): string {
		const h = (n: number) => n.toString(16).padStart(2, '0');
		return `#${h(r)}${h(g)}${h(b)}`;
	}
	function hexToRgb(hex: string): [number, number, number] {
		const m = hex.replace('#', '');
		const r = parseInt(m.slice(0, 2), 16);
		const g = parseInt(m.slice(2, 4), 16);
		const b = parseInt(m.slice(4, 6), 16);
		return [r, g, b];
	}

	const densityChoices: { id: 'L' | 'N' | 'M'; label: string; title: string }[] = [
		{
			id: 'L',
			label: 'L',
			title:
				'Least land — smallest pads (IPC-7351B least protrusion goals; parallels legacy density Level C / minimum land).'
		},
		{
			id: 'N',
			label: 'N',
			title: 'Nominal land — median between L and M (parallels legacy Level B).'
		},
		{
			id: 'M',
			label: 'M',
			title:
				'Most land — largest pads (IPC-7351B most protrusion goals; parallels legacy density Level A / maximum land).'
		}
	];

	const sizeChoices = (['01005', '0201', '0402', '0603', '0805', '1206', '1210'] as const).map(
		(id) => ({
			id,
			label: EIA_CASE_SIZE_LABELS[id] ?? id
		})
	);

	function toggleGlobal<T extends string>(arr: T[], id: T) {
		const idx = arr.indexOf(id);
		if (idx >= 0) arr.splice(idx, 1);
		else arr.push(id);
	}

	const colorRows: {
		key: keyof typeof appState.config.settings.colors;
		label: string;
		fields: string[];
	}[] = [
		{ key: 'default', label: 'Default fallback', fields: ['body'] },
		{ key: 'capc', label: 'CAPC (capacitors)', fields: ['body', 'terminal'] },
		{ key: 'indc', label: 'INDC (inductors)', fields: ['body', 'terminal'] },
		{ key: 'fb', label: 'FB (ferrite beads)', fields: ['body', 'terminal'] },
		{ key: 'resc', label: 'RESC (resistors)', fields: ['substrate', 'passivation', 'terminal'] }
	];
</script>

<SectionHeader
	title="Project settings"
	description="Project-wide settings consumed by hlcl/_config.py. Globals below set the defaults that per-family “Use global” inherits; the Libraries tab can then override specific options per family."
/>

<div class="mt-6 grid gap-8 lg:grid-cols-2">
	<section class="space-y-4 rounded-lg border border-ink-200 bg-white p-6">
		<header>
			<h3 class="text-sm font-semibold tracking-wider text-navy-700 uppercase">Globals</h3>
			<p class="mt-1 text-xs text-ink-500">
				Default values that per-family options inherit when set to “Use global”.
			</p>
		</header>
		<div class="flex flex-col gap-6">
			<div class="min-w-0">
				<div class="text-xs font-medium text-ink-700">Density variants</div>
				<div class="mt-1.5 flex gap-1.5">
					{#each densityChoices as d (d.id)}
						{@const active = appState.config.settings.hlcl.enabled_densities.includes(d.id)}
						<button
							type="button"
							title={d.title}
							class={[
								'flex-1 rounded border py-1.5 text-center text-xs font-semibold transition',
								active
									? 'border-emerald-400 bg-emerald-50 text-emerald-900 ring-1 ring-emerald-200 ring-inset'
									: 'border-ink-200 bg-white text-ink-400 hover:border-ink-300'
							]}
							onclick={() => toggleGlobal(appState.config.settings.hlcl.enabled_densities, d.id)}
						>
							{d.label}
						</button>
					{/each}
				</div>
				<!-- IPC-7351B Tables 3-5 / 3-6: L/N/M = least / nominal / most *land protrusion* (pad oversize); see hlcl/house/altium_pcblib/ipc.py -->
				<p class="mt-2 text-[11px] leading-relaxed text-ink-500">
					IPC-7351B labels these by pad <span class="italic">protrusion</span> goals (toe/side):
					<strong class="font-medium text-ink-700">L</strong>
					least — smallest pads;
					<strong class="font-medium text-ink-700">N</strong>
					nominal;
					<strong class="font-medium text-ink-700">M</strong>
					most — largest pads. This is not GD&T “material condition” on the component; legacy IPC-SM-782
					density levels are usually written
					<span class="font-mono text-ink-600">C / B / A</span>
					for least → nominal → most land (same ordering as
					<span class="font-mono text-ink-600">L / N / M</span>
					here).
				</p>
			</div>
			<div class="min-w-0">
				<div class="text-xs font-medium text-ink-700">Case sizes</div>
				<div class="mt-1.5 flex flex-wrap gap-1.5">
					{#each sizeChoices as s (s.id)}
						{@const active = appState.config.settings.hlcl.enabled_sizes.includes(s.id)}
						<button
							type="button"
							class={[
								'rounded border px-2 py-1 font-mono text-[11px] font-medium transition',
								active
									? 'border-emerald-400 bg-emerald-50 text-emerald-900 ring-1 ring-emerald-200 ring-inset'
									: 'border-ink-200 bg-white text-ink-400 hover:border-ink-300'
							]}
							onclick={() => toggleGlobal(appState.config.settings.hlcl.enabled_sizes, s.id)}
						>
							{s.label}
						</button>
					{/each}
				</div>
				<p class="mt-2 text-[11px] leading-relaxed text-ink-500">
					Buttons use <strong class="font-medium text-ink-700">imperial EIA</strong> chip-size codes
					(inch-based naming, e.g. 0603 ≈ 0.06″×0.03″). Values in parentheses are the usual
					<strong class="font-medium text-ink-700">metric IEC</strong> length×width codes in 0.01&nbsp;mm
					units (e.g. 1608 ⇒ 1.6&nbsp;mm × 0.8&nbsp;mm).
				</p>
			</div>
		</div>
	</section>

	<section class="space-y-4 rounded-lg border border-ink-200 bg-white p-6">
		<header>
			<h3 class="text-sm font-semibold tracking-wider text-navy-700 uppercase">
				IPC-7351B pad math
			</h3>
			<p class="mt-1 text-xs text-ink-500">
				Tolerance terms F (fabrication) and P (placement) used by the §3.1.4 pad-extent equations.
			</p>
		</header>
		<NumberField
			label="Fabrication tolerance F"
			bind:value={appState.config.settings.ipc.fabrication_tolerance_mm}
			min={0}
			max={1}
			step={0.01}
			unit="mm"
		/>
		<NumberField
			label="Placement tolerance P"
			bind:value={appState.config.settings.ipc.placement_tolerance_mm}
			min={0}
			max={1}
			step={0.01}
			unit="mm"
		/>
	</section>

	<section class="space-y-4 rounded-lg border border-ink-200 bg-white p-6">
		<header>
			<h3 class="text-sm font-semibold tracking-wider text-navy-700 uppercase">
				HLCL drawing standards
			</h3>
			<p class="mt-1 text-xs text-ink-500">
				Mirrors house/altium_pcblib/hlcl.py — pad corner radius, mask expansion, sliver enforcement.
			</p>
		</header>
		<NumberField
			label="Pad corner radius"
			bind:value={appState.config.settings.hlcl.pad_corner_radius_percent}
			min={0}
			max={50}
			step={1}
			unit="%"
		/>
		<NumberField
			label="Solder mask expansion"
			bind:value={appState.config.settings.hlcl.solder_mask_expansion_mm}
			min={0}
			max={1}
			step={0.01}
			unit="mm"
		/>
		<NumberField
			label="Min mask sliver"
			bind:value={appState.config.settings.hlcl.min_solder_mask_sliver_mm}
			min={0}
			max={1}
			step={0.01}
			unit="mm"
		/>
		<NumberField
			label="Outline line width"
			bind:value={appState.config.settings.hlcl.outline_line_width_mm}
			min={0}
			max={1}
			step={0.01}
			unit="mm"
		/>
		<NumberField
			label="Max crosshair half-arm"
			bind:value={appState.config.settings.hlcl.max_crosshair_half_arm_mm}
			min={0}
			max={2}
			step={0.05}
			unit="mm"
		/>
		<NumberField
			label="Component body standoff"
			bind:value={appState.config.settings.hlcl.component_body_standoff_mm}
			min={0}
			max={5}
			step={0.05}
			unit="mm"
		/>
	</section>

	<section class="space-y-4 rounded-lg border border-ink-200 bg-white p-6">
		<header>
			<h3 class="text-sm font-semibold tracking-wider text-navy-700 uppercase">STEP geometry</h3>
			<p class="mt-1 text-xs text-ink-500">
				Tunables for the parametric 3D model generator (house/stepgen).
			</p>
		</header>
		<NumberField
			label="Default fillet radius"
			bind:value={appState.config.settings.stepgen.default_fillet_radius_mm}
			min={0}
			max={1}
			step={0.01}
			unit="mm"
		/>
		<NumberField
			label="RESC metal thickness fraction"
			bind:value={appState.config.settings.stepgen.resc_metal_thickness_fraction}
			min={0}
			max={0.5}
			step={0.01}
		/>
		<NumberField
			label="RESC metal thickness floor"
			bind:value={appState.config.settings.stepgen.resc_metal_thickness_floor_mm}
			min={0}
			max={0.5}
			step={0.005}
			unit="mm"
		/>
	</section>

	<section class="space-y-4 rounded-lg border border-ink-200 bg-white p-6 lg:col-span-2">
		<header>
			<h3 class="text-sm font-semibold tracking-wider text-navy-700 uppercase">Family colours</h3>
			<p class="mt-1 text-xs text-ink-500">
				24-bit RGB. Used by both the .PcbLib BodyColor3D and the parametric STEP COLOUR_RGB tuples.
			</p>
		</header>
		<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
			{#each colorRows as row (row.key)}
				<div class="rounded-md border border-ink-200 bg-ink-50 p-3">
					<div class="text-xs font-medium text-ink-700">{row.label}</div>
					<div class="mt-2 flex flex-wrap gap-3">
						{#each row.fields as field (field)}
							{@const cur = (
								appState.config.settings.colors[row.key] as Record<string, [number, number, number]>
							)[field]}
							<label class="flex items-center gap-2 text-xs text-ink-600">
								<input
									type="color"
									class="h-7 w-7 cursor-pointer rounded border border-ink-300"
									value={rgbToHex(cur)}
									oninput={(e) => {
										const rgb = hexToRgb((e.target as HTMLInputElement).value);
										(
											appState.config.settings.colors[row.key] as Record<
												string,
												[number, number, number]
											>
										)[field] = rgb;
									}}
								/>
								<span class="font-mono">{field}</span>
							</label>
						{/each}
					</div>
				</div>
			{/each}
		</div>
	</section>
</div>
