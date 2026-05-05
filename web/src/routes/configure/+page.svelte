<script lang="ts">
	import Console from '$lib/components/Console.svelte';
	import PresetsTab from '$lib/components/tabs/PresetsTab.svelte';
	import LibrariesTab from '$lib/components/tabs/LibrariesTab.svelte';
	import ProjectSettingsTab from '$lib/components/tabs/ProjectSettingsTab.svelte';
	import PrioritiesTab from '$lib/components/tabs/PrioritiesTab.svelte';
	import BuildSettingsTab from '$lib/components/tabs/BuildSettingsTab.svelte';
	import CrosslinkingTab from '$lib/components/tabs/CrosslinkingTab.svelte';
	import PreviewTab from '$lib/components/tabs/PreviewTab.svelte';
	import GenerateTab from '$lib/components/tabs/GenerateTab.svelte';
	import MigrateTab from '$lib/components/tabs/MigrateTab.svelte';
	import { appState } from '$lib/state.svelte';
	let editingName = $state(false);

	function focusAndSelect(node: HTMLInputElement) {
		node.focus();
		node.select();
	}

	const isPreset = $derived(appState.activePresetId !== null);

	type TabId =
		| 'presets'
		| 'libraries'
		| 'project'
		| 'priorities'
		| 'crosslinks'
		| 'preview'
		| 'build'
		| 'generate'
		| 'migrate';

	const tabs: { id: TabId; label: string; subtitle: string }[] = [
		{ id: 'presets', label: '1 · Presets', subtitle: 'Start from a template' },
		{ id: 'libraries', label: '2 · Libraries', subtitle: 'Pick vendor families' },
		{ id: 'project', label: '3 · Settings', subtitle: 'IPC tolerances & globals' },
		{ id: 'priorities', label: '4 · Priorities', subtitle: 'Footprint precedence' },
		{ id: 'crosslinks', label: '5 · Crosslinks', subtitle: 'MPN substitutes' },
		{ id: 'preview', label: '6 · Preview', subtitle: 'Review the plan' },
		{ id: 'build', label: '7 · Build', subtitle: 'Artifacts to emit' },
		{ id: 'generate', label: '8 · Generate', subtitle: 'Run & download' },
		{ id: 'migrate', label: '9 · Migrate', subtitle: 'Import to Altium' }
	];

	let active: TabId = $state('presets');
	let consoleCollapsed = $state(false);

	function next() {
		const idx = tabs.findIndex((t) => t.id === active);
		if (idx >= 0 && idx < tabs.length - 1) active = tabs[idx + 1].id;
	}
	function prev() {
		const idx = tabs.findIndex((t) => t.id === active);
		if (idx > 0) active = tabs[idx - 1].id;
	}
</script>

<svelte:head>
	<title>Configure · HLCL</title>
</svelte:head>

<div class="flex flex-1 flex-col">
	<div class="border-b border-ink-200 bg-white">
		<div class="mx-auto max-w-7xl px-6 pt-6">
			<!-- Configuration identity row: editable name + Preset / Custom badge -->
			<div class="flex flex-wrap items-center gap-3">
				<span class="text-xs font-semibold tracking-[0.15em] text-ink-400 uppercase">
					Configuration
				</span>

				<!-- Inline editable name -->
				{#if editingName}
					<input
						type="text"
						class="min-w-0 flex-1 rounded border border-navy-300 bg-white px-2 py-0.5 text-lg font-bold text-ink-900 shadow-sm focus:border-navy-500 focus:ring-1 focus:ring-navy-500 focus:outline-none sm:flex-none sm:text-xl"
						bind:value={appState.configName}
						onblur={() => (editingName = false)}
						onkeydown={(e) => {
							if (e.key === 'Enter' || e.key === 'Escape') editingName = false;
						}}
						use:focusAndSelect
					/>
				{:else}
					<button
						type="button"
						class="group flex items-center gap-1.5 rounded px-1 py-0.5 text-xl font-bold text-ink-900 transition hover:bg-ink-100"
						onclick={() => (editingName = true)}
						title="Click to rename"
					>
						{appState.configName}
						<svg
							class="h-3.5 w-3.5 text-ink-400 opacity-0 transition group-hover:opacity-100"
							viewBox="0 0 20 20"
							fill="currentColor"
						>
							<path
								d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"
							/>
						</svg>
					</button>
				{/if}

				<!-- Preset / Custom badge -->
				{#if isPreset}
					<span
						class="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-200 ring-inset"
					>
						<span class="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
						Preset
					</span>
				{:else}
					<span
						class="inline-flex items-center gap-1.5 rounded-full bg-ink-100 px-2.5 py-1 text-xs font-semibold text-ink-600 ring-1 ring-ink-200 ring-inset"
					>
						<span class="h-1.5 w-1.5 rounded-full bg-ink-400"></span>
						Custom
					</span>
				{/if}
			</div>

			<p class="mt-1.5 text-xs text-ink-500">
				Walk through the nine steps. Settings persist in this browser between visits.
			</p>

			<nav class="mt-4 -mb-px flex gap-1 overflow-x-auto" aria-label="Workflow tabs">
				{#each tabs as tab (tab.id)}
					<button
						type="button"
						onclick={() => (active = tab.id)}
						class={[
							'group flex shrink-0 flex-col items-start gap-0.5 border-b-2 px-4 py-3 text-left transition',
							active === tab.id ? 'border-accent-500' : 'border-transparent hover:border-ink-300'
						]}
						aria-current={active === tab.id ? 'page' : undefined}
					>
						<span
							class={[
								'text-sm font-semibold transition',
								active === tab.id ? 'text-ink-900' : 'text-ink-600 group-hover:text-ink-800'
							]}
						>
							{tab.label}
						</span>
						<span class="text-[11px] text-ink-500">{tab.subtitle}</span>
					</button>
				{/each}
			</nav>
		</div>
	</div>

	<div class="mx-auto w-full max-w-7xl flex-1 px-6 py-8">
		{#if active === 'presets'}
			<PresetsTab />
		{:else if active === 'libraries'}
			<LibrariesTab />
		{:else if active === 'project'}
			<ProjectSettingsTab />
		{:else if active === 'priorities'}
			<PrioritiesTab />
		{:else if active === 'build'}
			<BuildSettingsTab />
		{:else if active === 'crosslinks'}
			<CrosslinkingTab />
		{:else if active === 'preview'}
			<PreviewTab />
		{:else if active === 'generate'}
			<GenerateTab />
		{:else if active === 'migrate'}
			<MigrateTab />
		{/if}

		<div class="mt-10 flex items-center justify-between border-t border-ink-200 pt-6">
			<button
				type="button"
				onclick={prev}
				disabled={tabs[0].id === active}
				class="inline-flex items-center gap-2 rounded-md border border-ink-200 bg-white px-4 py-2 text-sm font-medium text-ink-700 shadow-sm hover:bg-ink-50 disabled:cursor-not-allowed disabled:opacity-40"
			>
				← Back
			</button>
			<button
				type="button"
				onclick={next}
				disabled={tabs[tabs.length - 1].id === active}
				class="inline-flex items-center gap-2 rounded-md bg-navy-900 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-navy-800 disabled:cursor-not-allowed disabled:opacity-40"
			>
				Next →
			</button>
		</div>
	</div>

	<Console bind:collapsed={consoleCollapsed} />
</div>
