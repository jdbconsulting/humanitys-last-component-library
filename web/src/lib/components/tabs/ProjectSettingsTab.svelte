<script lang="ts">
	import { appState } from '$lib/state.svelte';
	import NumberField from '../NumberField.svelte';
	import SectionHeader from '../SectionHeader.svelte';

	function moveUp(idx: number) {
		if (idx <= 0) return;
		const arr = appState.project.priority;
		[arr[idx - 1], arr[idx]] = [arr[idx], arr[idx - 1]];
	}
	function moveDown(idx: number) {
		const arr = appState.project.priority;
		if (idx >= arr.length - 1) return;
		[arr[idx + 1], arr[idx]] = [arr[idx], arr[idx + 1]];
	}

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

	const colorRows: {
		key: keyof typeof appState.project.colors;
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
	description="Project-wide settings that mirror house/settings.toml. Per-family overrides on the previous tab can override these on a per-family basis."
/>

<div class="mt-6 grid gap-8 lg:grid-cols-2">
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
			bind:value={appState.project.ipc.fabrication_tolerance_mm}
			min={0}
			max={1}
			step={0.01}
			unit="mm"
		/>
		<NumberField
			label="Placement tolerance P"
			bind:value={appState.project.ipc.placement_tolerance_mm}
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
			bind:value={appState.project.hlcl.pad_corner_radius_percent}
			min={0}
			max={50}
			step={1}
			unit="%"
		/>
		<NumberField
			label="Solder mask expansion"
			bind:value={appState.project.hlcl.solder_mask_expansion_mm}
			min={0}
			max={1}
			step={0.01}
			unit="mm"
		/>
		<NumberField
			label="Min mask sliver"
			bind:value={appState.project.hlcl.min_solder_mask_sliver_mm}
			min={0}
			max={1}
			step={0.01}
			unit="mm"
		/>
		<NumberField
			label="Outline line width"
			bind:value={appState.project.hlcl.outline_line_width_mm}
			min={0}
			max={1}
			step={0.01}
			unit="mm"
		/>
		<NumberField
			label="Max crosshair half-arm"
			bind:value={appState.project.hlcl.max_crosshair_half_arm_mm}
			min={0}
			max={2}
			step={0.05}
			unit="mm"
		/>
		<NumberField
			label="Component body standoff"
			bind:value={appState.project.hlcl.component_body_standoff_mm}
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
			bind:value={appState.project.stepgen.default_fillet_radius_mm}
			min={0}
			max={1}
			step={0.01}
			unit="mm"
		/>
		<NumberField
			label="RESC metal thickness fraction"
			bind:value={appState.project.stepgen.resc_metal_thickness_fraction}
			min={0}
			max={0.5}
			step={0.01}
		/>
		<NumberField
			label="RESC metal thickness floor"
			bind:value={appState.project.stepgen.resc_metal_thickness_floor_mm}
			min={0}
			max={0.5}
			step={0.005}
			unit="mm"
		/>
	</section>

	<section class="space-y-4 rounded-lg border border-ink-200 bg-white p-6">
		<header>
			<h3 class="text-sm font-semibold tracking-wider text-navy-700 uppercase">
				Vendor priority order
			</h3>
			<p class="mt-1 text-xs text-ink-500">
				Tie-break order when two vendor JSONs define the same FootprintName during the merge. Higher
				= wins.
			</p>
		</header>
		<ol class="space-y-1.5">
			{#each appState.project.priority as vendor, idx (vendor)}
				<li
					class="flex items-center gap-2 rounded border border-ink-200 bg-ink-50 px-3 py-1.5 text-sm"
				>
					<span class="w-6 text-right font-mono text-xs text-ink-400">#{idx + 1}</span>
					<span class="flex-1 font-mono text-xs text-ink-700">{vendor}</span>
					<button
						type="button"
						class="rounded p-1 text-ink-500 hover:bg-white hover:text-ink-800 disabled:opacity-30"
						onclick={() => moveUp(idx)}
						disabled={idx === 0}
						aria-label="Move up"
					>
						<svg class="h-3 w-3" viewBox="0 0 12 12" fill="currentColor"
							><path d="M6 3l4 5H2z" /></svg
						>
					</button>
					<button
						type="button"
						class="rounded p-1 text-ink-500 hover:bg-white hover:text-ink-800 disabled:opacity-30"
						onclick={() => moveDown(idx)}
						disabled={idx === appState.project.priority.length - 1}
						aria-label="Move down"
					>
						<svg class="h-3 w-3" viewBox="0 0 12 12" fill="currentColor"
							><path d="M6 9L2 4h8z" /></svg
						>
					</button>
				</li>
			{/each}
		</ol>
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
								appState.project.colors[row.key] as Record<string, [number, number, number]>
							)[field]}
							<label class="flex items-center gap-2 text-xs text-ink-600">
								<input
									type="color"
									class="h-7 w-7 cursor-pointer rounded border border-ink-300"
									value={rgbToHex(cur)}
									oninput={(e) => {
										const rgb = hexToRgb((e.target as HTMLInputElement).value);
										(appState.project.colors[row.key] as Record<string, [number, number, number]>)[
											field
										] = rgb;
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
