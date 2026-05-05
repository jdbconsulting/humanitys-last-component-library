<script lang="ts">
	import { appState } from '$lib/state.svelte';
	import { consoleLog } from '$lib/console.svelte';
	import { PRESETS, type Preset } from '$lib/presets';
	import SectionHeader from '../SectionHeader.svelte';

	let pendingApply = $state<string | null>(null);
	let fileInput = $state<HTMLInputElement | null>(null);
	let importError = $state<string | null>(null);

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
				const err = appState.importConfig(raw);
				if (err) {
					importError = err;
					consoleLog.error(`Import failed: ${err}`);
				} else {
					consoleLog.info(`Imported configuration "${appState.configName}" successfully.`);
					importError = null;
				}
			} catch {
				const msg = 'File is not valid JSON.';
				importError = msg;
				consoleLog.error(`Import failed: ${msg}`);
			}
			// Reset the input so the same file can be re-selected.
			if (fileInput) fileInput.value = '';
		};
		reader.readAsText(file);
	}

	const activeId = $derived(appState.activePresetId);
	const customised = $derived(activeId === null);

	function apply(preset: Preset) {
		appState.applyPreset(preset.id, preset.name, preset.delta);
		consoleLog.info(`Applied preset: ${preset.name}.`);
		pendingApply = null;
	}

	function requestApply(preset: Preset) {
		// First click stages the apply (so destructive overwrite is clearly two-step);
		// second click on the same preset commits.
		if (pendingApply === preset.id) {
			apply(preset);
		} else {
			pendingApply = preset.id;
		}
	}

	function cancelPending() {
		pendingApply = null;
	}

	const iconPaths: Record<Preset['icon'], string> = {
		// 24x24 viewBox, single path, currentColor stroke
		reset: 'M3 12a9 9 0 1015.5-6.3M19 4v6h-6',
		consumer: 'M3 9h18M5 9v10h14V9M9 5h6v4H9z',
		automotive: 'M5 16h14M7 16V9l2-3h6l2 3v7M7 13h10',
		precision: 'M12 3v18M5 12h14M8 6l8 12M16 6L8 18',
		voltage: 'M13 2L4 14h7l-2 8 9-12h-7l2-8z',
		all: 'M3 7h18M3 12h18M3 17h18'
	};
</script>

<!-- Hidden file input for JSON import -->
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

<div class="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-md border border-ink-200 bg-white px-4 py-3">
	<div class="flex items-center gap-2 text-sm">
		<span
			class={[
				'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium',
				customised
					? 'bg-ink-100 text-ink-600'
					: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200 ring-inset'
			]}
		>
			<span
				class={['h-1.5 w-1.5 rounded-full', customised ? 'bg-ink-400' : 'bg-emerald-500']}
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
				<path d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 9.293a1 1 0 011.414 0L9 10.586V4a1 1 0 112 0v6.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" />
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
		<strong class="font-semibold">Import error:</strong>
		{importError}
	</div>
{/if}

<div class="mt-6 grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
	{#each PRESETS as preset (preset.id)}
		{@const isActive = activeId === preset.id}
		{@const isPending = pendingApply === preset.id}
		<article
			class={[
				'relative flex flex-col rounded-lg border bg-white p-5 shadow-sm transition',
				isActive
					? 'border-emerald-300 ring-1 ring-emerald-200'
					: isPending
						? 'border-accent-400 ring-1 ring-accent-200'
						: 'border-ink-200 hover:border-ink-300 hover:shadow-md'
			]}
		>
			{#if isActive}
				<span
					class="absolute top-3 right-3 inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 ring-1 ring-emerald-200 ring-inset"
				>
					<span class="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
					Active
				</span>
			{/if}

			<div class="flex items-start gap-3">
				<span
					class={[
						'flex h-10 w-10 shrink-0 items-center justify-center rounded-md text-white shadow-sm',
						preset.icon === 'reset'
							? 'bg-ink-700'
							: preset.icon === 'voltage'
								? 'bg-accent-600'
								: 'bg-navy-900'
					]}
				>
					<svg
						class="h-5 w-5"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<path d={iconPaths[preset.icon]} />
					</svg>
				</span>
				<div class="min-w-0 flex-1">
					<div class="flex items-baseline gap-2">
						<h3 class="text-sm font-semibold text-ink-900">{preset.name}</h3>
						<span
							class="rounded bg-ink-100 px-1.5 py-0.5 font-mono text-[10px] font-medium text-ink-600"
						>
							{preset.tagline}
						</span>
					</div>
					<p class="mt-1 text-xs text-ink-600">{preset.summary}</p>
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

			{#if preset.delta.families}
				<div class="mt-4 border-t border-ink-100 pt-3">
					<div
						class="text-[10px] font-semibold tracking-[0.18em] text-ink-500 uppercase"
					>
						Enables
					</div>
					<div class="mt-1.5 flex flex-wrap gap-1">
						{#each preset.delta.families as fam (fam)}
							<span
								class="rounded bg-ink-100 px-1.5 py-0.5 font-mono text-[10px] font-medium text-ink-700"
							>
								{fam}
							</span>
						{/each}
					</div>
				</div>
			{/if}

			<div class="mt-5 flex items-center gap-2">
				{#if isActive}
					<button
						type="button"
						class="inline-flex flex-1 items-center justify-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-800 transition hover:bg-emerald-100"
						onclick={() => requestApply(preset)}
					>
						Re-apply
					</button>
				{:else if isPending}
					<button
						type="button"
						class="inline-flex flex-1 items-center justify-center gap-2 rounded-md bg-accent-500 px-3 py-2 text-sm font-semibold text-navy-950 shadow-sm transition hover:bg-accent-400"
						onclick={() => apply(preset)}
					>
						Confirm overwrite
					</button>
					<button
						type="button"
						class="rounded-md border border-ink-200 bg-white px-3 py-2 text-sm font-medium text-ink-700 hover:bg-ink-50"
						onclick={cancelPending}
					>
						Cancel
					</button>
				{:else}
					<button
						type="button"
						class="inline-flex flex-1 items-center justify-center gap-2 rounded-md bg-navy-900 px-3 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-navy-800"
						onclick={() => requestApply(preset)}
					>
						Apply preset
					</button>
				{/if}
			</div>

			{#if isPending}
				<p class="mt-2 text-[11px] text-amber-700">
					This will overwrite the Libraries, Project, and Build tabs. Cross-links are kept.
				</p>
			{/if}
		</article>
	{/each}
</div>

<div class="mt-8 rounded-md border border-dashed border-ink-300 bg-ink-50/60 p-4 text-xs text-ink-600">
	<strong class="font-semibold text-ink-700">Tip:</strong>
	Presets are a starting point — you can fine-tune anything they set on the later tabs.
	Once you do, the badge at the top will switch to <em class="not-italic">Custom configuration</em>.
</div>
