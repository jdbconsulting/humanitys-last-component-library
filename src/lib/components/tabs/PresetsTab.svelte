<script lang="ts">
	import { appState } from '$lib/state.svelte';
	import { consoleLog } from '$lib/console.svelte';
	import { PRESETS, type Preset } from '$lib/presets';
	import { allFamilies } from '$lib/libraries';
	import SectionHeader from '../SectionHeader.svelte';

	let fileInput = $state<HTMLInputElement | null>(null);
	let importError = $state<string[] | null>(null);

	/**
	 * Tracks the most recently applied preset so the card can briefly
	 * flash an "applied" cue. The `tick` field forces the derivation
	 * to change even when the same preset is re-applied (so re-apply
	 * still flashes); the timeout below resets the cue after ~1.8 s
	 * so the card returns to its resting active state.
	 */
	let justApplied = $state<{ id: string; tick: number } | null>(null);
	let appliedTimeout: ReturnType<typeof setTimeout> | null = null;

	function triggerImport() {
		importError = null;
		fileInput?.click();
	}

	function onFileSelected(e: Event) {
		const file = (e.target as HTMLInputElement).files?.[0];
		if (!file) return;
		const reader = new FileReader();
		reader.onload = (evt) => {
			try {
				const raw: unknown = JSON.parse(evt.target?.result as string);
				const errs = appState.importConfig(raw);
				if (errs) {
					importError = errs;
					for (const e of errs) consoleLog.error(`Import failed: ${e}`);
				} else {
					consoleLog.info(`Imported configuration "${appState.ui.config_name}.json" successfully.`);
					importError = null;
				}
			} catch {
				const msg = 'File is not valid JSON.';
				importError = [msg];
				consoleLog.error(`Import failed: ${msg}`);
			}
			if (fileInput) fileInput.value = '';
		};
		reader.readAsText(file);
	}

	const activeId = $derived(appState.ui.active_preset_id);
	const customised = $derived(activeId === null);

	/**
	 * Apply a preset wholesale on a single click — no confirmation
	 * step. The previous "Apply preset → Confirm overwrite" two-step
	 * was unreliable: the first click rendered a brand-new button at
	 * the same DOM position, which intermittently swallowed the
	 * second click. Cross-links are preserved by `applyPreset`, so
	 * the operation is non-destructive for hand-curated MPN data;
	 * only the per-tab settings change, and the user can switch
	 * presets again to undo.
	 */
	function apply(preset: Preset) {
		appState.applyPreset(preset.id, preset.title, preset.config);
		consoleLog.info(
			`Applied preset "${preset.title}" — ${enabledFamilyCount(preset)} of ${totalFamilyCount} families enabled.`
		);
		if (appliedTimeout) clearTimeout(appliedTimeout);
		justApplied = { id: preset.id, tick: (justApplied?.tick ?? 0) + 1 };
		appliedTimeout = setTimeout(() => {
			justApplied = null;
			appliedTimeout = null;
		}, 1800);
	}

	/**
	 * Count the number of vendor families a preset would enable.
	 * Surfaced as a small "N of <total> on" pill on each card so
	 * authors can sanity-check at a glance that they're picking up
	 * the family set they expect. Presets only enumerate their
	 * enabled families (the rest are backfilled by `applyPreset`)
	 * so the count is just `families.values().filter(enabled)`.
	 */
	function enabledFamilyCount(preset: Preset): number {
		return Object.values(preset.config.families).filter((f) => f.enabled).length;
	}
	/**
	 * Total catalog-known family count, sourced from the merged
	 * `_generated/catalog.ts`. Using the catalog rather than reading
	 * keys off any one preset means newly-dropped vendor folders
	 * bump this number automatically without anyone having to
	 * remember to refresh a preset file. Cached as a $derived so
	 * the subscription tracks if the catalog is ever made reactive.
	 */
	const totalFamilyCount = $derived(allFamilies().length);

	/**
	 * One shared icon across every preset card — a stacked-layers glyph
	 * that reads as "saved configuration / template".
	 */
	const PRESET_ICON_PATH = 'M12 3l9 4-9 4-9-4 9-4zM3 12l9 4 9-4M3 17l9 4 9-4';
</script>

<input
	bind:this={fileInput}
	type="file"
	accept=".json,application/json"
	class="sr-only"
	onchange={onFileSelected}
/>

<SectionHeader
	title="Presets"
	description="Start from a known-good combination of vendor families, IPC tolerances, and build outputs. Every preset overlays on top of factory defaults — applying a preset overwrites the Libraries, Settings, and Build tabs but leaves your cross-links untouched."
/>

<div
	class="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-md border border-ink-200 bg-white px-4 py-3"
>
	<div class="flex items-center gap-2 text-sm">
		<span
			class={[
				'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium',
				customised
					? 'bg-ink-100 text-ink-600'
					: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200 ring-inset'
			]}
		>
			<span class={['h-1.5 w-1.5 rounded-full', customised ? 'bg-ink-400' : 'bg-emerald-500']}
			></span>
			{customised ? 'Custom' : 'Preset'}
		</span>
		<span class="text-xs text-ink-500">
			Edits in any later tab will mark the configuration as “custom”.
		</span>
	</div>
	<div class="flex items-center gap-3">
		<button
			type="button"
			class="inline-flex items-center gap-1.5 text-xs font-medium text-navy-700 underline-offset-2 hover:text-navy-900 hover:underline"
			onclick={triggerImport}
			title="Import a previously exported configuration JSON"
		>
			<svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
				<path
					d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 9.293a1 1 0 011.414 0L9 10.586V4a1 1 0 112 0v6.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z"
				/>
			</svg>
			Import JSON
		</button>
		<span class="text-ink-300">|</span>
		<button
			type="button"
			class="text-xs font-medium text-ink-600 underline-offset-2 hover:text-ink-900 hover:underline"
			onclick={() => {
				appState.resetAll();
				consoleLog.info('All settings reset to factory defaults.');
			}}
		>
			Reset everything
		</button>
	</div>
</div>

{#if importError}
	<div class="mt-2 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
		<strong class="font-semibold">Import error{importError.length > 1 ? 's' : ''}:</strong>
		<ul class="mt-1 list-disc pl-4">
			{#each importError as err (err)}
				<li class="font-mono">{err}</li>
			{/each}
		</ul>
	</div>
{/if}

<div class="mt-6 grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
	{#each PRESETS as preset (preset.id)}
		{@const isActive = activeId === preset.id}
		{@const flashing = justApplied?.id === preset.id}
		{@const familiesOn = enabledFamilyCount(preset)}
		<article
			class={[
				'relative flex flex-col rounded-lg border bg-white p-5 shadow-sm transition',
				flashing
					? 'border-emerald-400 ring-2 ring-emerald-300'
					: isActive
						? 'border-emerald-300 ring-1 ring-emerald-200'
						: 'border-ink-200 hover:border-ink-300 hover:shadow-md'
			]}
		>
			{#if isActive}
				<span
					class="absolute top-3 right-3 inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 ring-1 ring-emerald-200 ring-inset"
				>
					<span class="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
					{flashing ? 'Just applied' : 'Active'}
				</span>
			{/if}

			<div class="flex items-start gap-3">
				<span
					class="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-navy-900 text-white shadow-sm"
				>
					<svg
						class="h-5 w-5"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.75"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<path d={PRESET_ICON_PATH} />
					</svg>
				</span>
				<div class="min-w-0 flex-1">
					<div class="flex flex-wrap items-baseline gap-x-2 gap-y-1">
						<h3 class="text-sm font-semibold text-ink-900">{preset.title}</h3>
						<span
							class="rounded bg-ink-100 px-1.5 py-0.5 font-mono text-[10px] font-medium text-ink-600"
						>
							{preset.tagline}
						</span>
					</div>
					<p class="mt-1 text-xs leading-relaxed text-ink-600">{preset.description}</p>
				</div>
			</div>

			<ul class="mt-4 flex-1 space-y-1.5">
				{#each preset.bullets as bullet (bullet)}
					<li class="flex items-start gap-2 text-xs text-ink-700">
						<svg
							class="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-500"
							viewBox="0 0 20 20"
							fill="currentColor"
						>
							<path
								fill-rule="evenodd"
								d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
								clip-rule="evenodd"
							/>
						</svg>
						<span>{bullet}</span>
					</li>
				{/each}
			</ul>

			<div class="mt-4 flex items-center justify-between border-t border-ink-100 pt-3">
				<div class="text-[10px] font-semibold tracking-[0.18em] text-ink-500 uppercase">
					Vendor families
				</div>
				<span
					class="rounded bg-ink-100 px-1.5 py-0.5 font-mono text-[10px] font-medium text-ink-700"
					title="Number of vendor families this preset enables out of the catalog total"
				>
					{familiesOn} / {totalFamilyCount} on
				</span>
			</div>

			<div class="mt-4 flex items-center gap-2">
				{#if isActive}
					<button
						type="button"
						class="inline-flex flex-1 items-center justify-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-800 transition hover:bg-emerald-100"
						onclick={() => apply(preset)}
					>
						Re-apply
					</button>
				{:else}
					<button
						type="button"
						class="inline-flex flex-1 items-center justify-center gap-2 rounded-md bg-navy-900 px-3 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-navy-800"
						onclick={() => apply(preset)}
					>
						Apply preset
					</button>
				{/if}
			</div>
		</article>
	{/each}
</div>

<div
	class="mt-8 rounded-md border border-dashed border-ink-300 bg-ink-50/60 p-4 text-xs text-ink-600"
>
	<strong class="font-semibold text-ink-700">Tip:</strong>
	Presets are a starting point — you can fine-tune anything they set on the later tabs. Once you do, the
	badge at the top will switch to <em class="not-italic">Custom configuration</em>.
</div>
