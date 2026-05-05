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
	import { sanitizeConfigFilenameStem } from '$lib/config-filename';
	let editingName = $state(false);
	let editStem = $state('');

	function focusAndSelect(node: HTMLInputElement) {
		node.focus();
		node.select();
	}

	function startEditingName() {
		editStem = appState.ui.config_name;
		editingName = true;
	}

	function commitConfigStem() {
		if (!editingName) return;
		const stem = sanitizeConfigFilenameStem(editStem);
		appState.ui = { ...appState.ui, config_name: stem };
		editingName = false;
	}

	function cancelEditingName() {
		editingName = false;
	}

	const isPreset = $derived(appState.ui.active_preset_id !== null);

	/**
	 * Library-stats banner. Two of the three numbers — `components`
	 * and `unique_footprints` — are sourced from the most recent
	 * in-browser build via `appState.ui.build_stats`, and are gated on
	 * the cached `config_hash` matching the live `BuildConfig`: when
	 * it does, the numbers render in navy; when it doesn't (or there
	 * is no cached build at all), they fade to "???" and a tiny
	 * "rebuild to calculate" link appears below the banner.
	 *
	 * The `families` count is computed directly from the live config
	 * (it's just the number of enabled families in the Libraries tab)
	 * so it never goes stale and never needs a build to populate.
	 */
	const statsFresh = $derived(appState.buildStatsAreFresh());
	const cachedStats = $derived(appState.ui.build_stats?.stats ?? null);
	const liveFamilyCount = $derived(appState.enabledFamilyIds().length);

	function formatInt(n: number): string {
		return n.toLocaleString();
	}

	/**
	 * For build-derived stats (components, unique_footprints): the
	 * live formatted number when the cached stats line up with the
	 * live config, or a literal "???" otherwise. Returning the
	 * literal rather than `formatInt(0)` lets the banner clearly
	 * distinguish "we don't know yet" from "the build legitimately
	 * produced zero".
	 */
	function buildDerivedStat(
		getter: (s: { components: number; unique_footprints: number }) => number
	): string {
		if (statsFresh && cachedStats) return formatInt(getter(cachedStats));
		return '???';
	}

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
		{ id: 'migrate', label: '9 · Use', subtitle: 'ECAD scripts' }
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
			<!-- Configuration identity row: file name + badge · library stats banner -->
			<div class="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
				<div class="flex min-w-0 flex-wrap items-center gap-3">
					<span class="text-xs font-semibold tracking-[0.15em] text-ink-400 uppercase">
						Configuration file
					</span>

					<!-- File stem (editable) + literal .json suffix -->
					{#if editingName}
						<div class="flex min-w-0 flex-1 items-baseline gap-0.5 sm:flex-none">
							<input
								type="text"
								spellcheck="false"
								autocomplete="off"
								aria-label="Configuration file name without extension"
								class="min-w-[8rem] flex-1 rounded border border-navy-300 bg-white px-2 py-0.5 text-lg font-bold text-ink-900 shadow-sm focus:border-navy-500 focus:ring-1 focus:ring-navy-500 focus:outline-none sm:min-w-[12rem] sm:text-xl"
								bind:value={editStem}
								onblur={commitConfigStem}
								onkeydown={(e) => {
									if (e.key === 'Enter') {
										e.preventDefault();
										(e.target as HTMLInputElement).blur();
									}
									if (e.key === 'Escape') {
										e.preventDefault();
										cancelEditingName();
									}
								}}
								use:focusAndSelect
							/>
							<span
								class="shrink-0 text-lg font-bold text-ink-400 select-none sm:text-xl"
								aria-hidden="true"
							>
								.json
							</span>
						</div>
					{:else}
						<button
							type="button"
							class="group flex items-baseline gap-0.5 rounded px-1 py-0.5 text-xl font-bold transition hover:bg-ink-100"
							onclick={startEditingName}
							title="Click to edit file name"
						>
							<span class="text-ink-900">{appState.ui.config_name}</span>
							<span class="font-bold text-ink-400 select-none">.json</span>
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

				<div class="flex shrink-0 flex-col gap-0.5 sm:ml-2">
					<div
						class={[
							'flex flex-wrap items-stretch divide-x divide-ink-200 rounded-lg border bg-gradient-to-br px-1 py-1 shadow-sm ring-1 ring-inset',
							statsFresh
								? 'border-ink-200 from-navy-50/80 to-white ring-ink-100'
								: 'border-ink-200 from-ink-50 to-white ring-ink-100'
						]}
						role="group"
						aria-label={statsFresh
							? 'Library statistics from the most recent build'
							: 'Library statistics — stale, run a build to refresh'}
						title={statsFresh
							? 'Computed from the most recent in-browser build.'
							: 'These numbers are out of date because you have edited the configuration since the last build. Click "rebuild to calculate" below.'}
					>
						<div class="flex min-w-[5.5rem] flex-1 flex-col px-3 py-1.5 sm:min-w-0 sm:flex-initial">
							<span class="text-[10px] font-semibold tracking-wide text-ink-500 uppercase"
								>Components</span
							>
							<span
								class={[
									'font-mono text-sm font-semibold tabular-nums',
									statsFresh ? 'text-navy-900' : 'text-ink-400'
								]}
							>
								{buildDerivedStat((s) => s.components)}
							</span>
						</div>
						<div class="flex min-w-[5.5rem] flex-1 flex-col px-3 py-1.5 sm:min-w-0 sm:flex-initial">
							<span
								class="text-[10px] leading-tight font-semibold tracking-wide text-ink-500 uppercase"
								>Unique footprints</span
							>
							<span
								class={[
									'font-mono text-sm font-semibold tabular-nums',
									statsFresh ? 'text-navy-900' : 'text-ink-400'
								]}
							>
								{buildDerivedStat((s) => s.unique_footprints)}
							</span>
						</div>
						<div
							class="flex min-w-[5.5rem] flex-1 flex-col px-3 py-1.5 sm:min-w-0 sm:flex-initial"
							title="Families enabled in the current configuration. Updates live as you toggle families on the Libraries tab — no build required."
						>
							<span class="text-[10px] font-semibold tracking-wide text-ink-500 uppercase"
								>Families</span
							>
							<span class="font-mono text-sm font-semibold text-navy-900 tabular-nums">
								{formatInt(liveFamilyCount)}
							</span>
						</div>
					</div>

					{#if !statsFresh}
						<button
							type="button"
							onclick={() => (active = 'generate')}
							class="self-end pt-0.5 pr-2 text-[10px] font-medium text-ink-500 underline-offset-2 transition hover:text-navy-700 hover:underline"
							title="Jump to the Generate tab and run a build to refresh these numbers"
						>
							{cachedStats ? 'stats are stale · ' : 'no build yet · '}rebuild to calculate →
						</button>
					{/if}
				</div>
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
