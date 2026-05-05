<script lang="ts">
	import { appState } from '$lib/state.svelte';
	import { consoleLog } from '$lib/console.svelte';
	import {
		computeBuildPlan,
		formatOptionValue,
		serializeSettingsToml,
		summarizeEnabledFamilies,
		type BuildStep
	} from '$lib/preview';
	import SectionHeader from '../SectionHeader.svelte';

	const snapshot = $derived(appState.snapshot());
	const settingsToml = $derived(serializeSettingsToml(snapshot.project));
	const buildPlan = $derived(computeBuildPlan(snapshot));
	const enabledFamilies = $derived(summarizeEnabledFamilies(snapshot));
	const configJson = $derived(JSON.stringify(snapshot, null, 2));

	const stageColors: Record<BuildStep['stage'], string> = {
		vendor: 'bg-navy-100 text-navy-800 ring-navy-200',
		merge: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
		step: 'bg-violet-50 text-violet-800 ring-violet-200',
		pcblib: 'bg-accent-100 text-accent-900 ring-accent-200',
		schlib: 'bg-sky-50 text-sky-800 ring-sky-200',
		standards: 'bg-rose-50 text-rose-800 ring-rose-200',
		package: 'bg-ink-200 text-ink-800 ring-ink-300'
	};

	let copyState = $state<{ kind: 'idle' | 'copied' | 'failed'; key?: string }>({ kind: 'idle' });

	async function copyToClipboard(text: string, key: string): Promise<void> {
		try {
			await navigator.clipboard.writeText(text);
			copyState = { kind: 'copied', key };
			consoleLog.info(`Copied ${key} to clipboard (${text.length} chars).`);
		} catch (err) {
			copyState = { kind: 'failed', key };
			consoleLog.warn(`Clipboard copy failed: ${err instanceof Error ? err.message : String(err)}`);
		}
		setTimeout(() => {
			copyState = { kind: 'idle' };
		}, 1800);
	}

	function downloadText(filename: string, mime: string, body: string) {
		const blob = new Blob([body], { type: mime });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = filename;
		document.body.appendChild(a);
		a.click();
		a.remove();
		URL.revokeObjectURL(url);
		consoleLog.info(`Downloaded ${filename} (${body.length} bytes).`);
	}

	const overview = $derived({
		families: enabledFamilies.length,
		artifacts: buildPlan.length,
		crosslinks: snapshot.crosslinks.length,
		mergePriorityHead: snapshot.project.priority.slice(0, 4)
	});
</script>

<SectionHeader
	title="Preview"
	description="Final once-over before generation. Everything below is computed live from your current selections — edit any prior tab and the preview re-renders."
/>

<div class="mt-6 space-y-8">
	<!-- Overview metric tiles -->
	<section class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
		<div class="rounded-lg border border-ink-200 bg-white p-5 shadow-sm">
			<div class="text-[11px] font-semibold tracking-[0.18em] text-ink-500 uppercase">
				Families enabled
			</div>
			<div class="mt-2 flex items-baseline gap-2">
				<span class="text-3xl font-bold text-ink-900">{overview.families}</span>
				<span class="text-xs text-ink-500">vendor libraries</span>
			</div>
		</div>
		<div class="rounded-lg border border-ink-200 bg-white p-5 shadow-sm">
			<div class="text-[11px] font-semibold tracking-[0.18em] text-ink-500 uppercase">
				Build steps
			</div>
			<div class="mt-2 flex items-baseline gap-2">
				<span class="text-3xl font-bold text-ink-900">{overview.artifacts}</span>
				<span class="text-xs text-ink-500">make targets</span>
			</div>
		</div>
		<div class="rounded-lg border border-ink-200 bg-white p-5 shadow-sm">
			<div class="text-[11px] font-semibold tracking-[0.18em] text-ink-500 uppercase">
				Cross-links
			</div>
			<div class="mt-2 flex items-baseline gap-2">
				<span class="text-3xl font-bold text-ink-900">{overview.crosslinks}</span>
				<span class="text-xs text-ink-500">MPN substitutes</span>
			</div>
		</div>
		<div class="rounded-lg border border-ink-200 bg-white p-5 shadow-sm">
			<div class="text-[11px] font-semibold tracking-[0.18em] text-ink-500 uppercase">
				Tie-break head
			</div>
			<div class="mt-2 flex flex-wrap gap-1">
				{#each overview.mergePriorityHead as v, i (v)}
					<span
						class={[
							'rounded px-1.5 py-0.5 font-mono text-[10px] font-medium',
							i === 0 ? 'bg-accent-100 text-accent-900' : 'bg-ink-100 text-ink-700'
						]}
					>
						{i + 1}. {v}
					</span>
				{/each}
				{#if snapshot.project.priority.length > 4}
					<span class="self-center text-xs text-ink-500"
						>+{snapshot.project.priority.length - 4} more</span
					>
				{/if}
			</div>
		</div>
	</section>

	<!-- Build plan -->
	<section class="rounded-lg border border-ink-200 bg-white shadow-sm">
		<header class="flex items-baseline justify-between border-b border-ink-200 px-6 py-4">
			<div>
				<h3 class="text-sm font-semibold tracking-[0.18em] text-navy-900 uppercase">Build plan</h3>
				<p class="mt-0.5 text-xs text-ink-500">
					Ordered list of the Python entry points the in-browser pipeline will run.
				</p>
			</div>
			<span class="font-mono text-xs text-ink-500">{buildPlan.length} steps</span>
		</header>

		{#if buildPlan.length === 0}
			<div class="px-6 py-10 text-center text-sm text-ink-500">
				Nothing to do yet. Enable at least one family on the
				<em class="not-italic text-ink-700">Libraries</em> tab and toggle build outputs on the
				<em class="not-italic text-ink-700">Build</em> tab.
			</div>
		{:else}
			<ol class="divide-y divide-ink-100">
				{#each buildPlan as step, i (step.id)}
					<li class="flex gap-4 px-6 py-4">
						<span
							class="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-navy-900 font-mono text-[11px] font-semibold text-white"
						>
							{i + 1}
						</span>
						<div class="flex-1">
							<div class="flex flex-wrap items-baseline gap-2">
								<span class="text-sm font-semibold text-ink-900">{step.title}</span>
								<span
									class={[
										'rounded px-1.5 py-0.5 font-mono text-[10px] font-medium ring-1 ring-inset',
										stageColors[step.stage]
									]}
								>
									{step.stage}
								</span>
								<span class="font-mono text-[11px] text-ink-500">
									$ make {step.target}
								</span>
							</div>
							<p class="mt-1 text-xs text-ink-600">{step.detail}</p>
							{#if step.outputs.length > 0}
								<ul class="mt-2 space-y-0.5">
									{#each step.outputs as out (out)}
										<li class="font-mono text-[11px] text-ink-700">
											<span class="text-emerald-600">→</span>
											{out}
										</li>
									{/each}
								</ul>
							{/if}
						</div>
					</li>
				{/each}
			</ol>
		{/if}
	</section>

	<!-- Enabled families with overrides surfaced -->
	<section class="rounded-lg border border-ink-200 bg-white shadow-sm">
		<header class="flex items-baseline justify-between border-b border-ink-200 px-6 py-4">
			<div>
				<h3 class="text-sm font-semibold tracking-[0.18em] text-navy-900 uppercase">
					Enabled families
				</h3>
				<p class="mt-0.5 text-xs text-ink-500">
					Per-family overrides surfaced. Anything left on “Use global” is omitted.
				</p>
			</div>
			<span class="font-mono text-xs text-ink-500">{enabledFamilies.length}</span>
		</header>

		{#if enabledFamilies.length === 0}
			<div class="px-6 py-10 text-center text-sm text-ink-500">
				No families enabled. Pick at least one on the Libraries tab.
			</div>
		{:else}
			<ul class="divide-y divide-ink-100">
				{#each enabledFamilies as fam (fam.id)}
					<li class="px-6 py-4">
						<div class="flex flex-wrap items-baseline gap-2">
							<span class="text-sm font-semibold text-ink-900">{fam.def.name}</span>
							<span
								class="rounded bg-ink-100 px-1.5 py-0.5 font-mono text-[10px] font-medium text-ink-600"
							>
								{fam.id}
							</span>
							<span class="text-xs text-ink-500">·</span>
							<span class="text-xs text-ink-600">{fam.def.summary}</span>
						</div>
						{#if fam.overriddenOptions.length === 0}
							<p class="mt-1 text-xs text-ink-500">
								<span class="font-medium text-ink-600">Inherits all globals.</span>
							</p>
						{:else}
							<dl class="mt-2 grid gap-x-6 gap-y-1 sm:grid-cols-2">
								{#each fam.overriddenOptions as opt (opt.id)}
									<div class="flex flex-wrap items-baseline gap-2 text-xs">
										<dt class="text-ink-500">{opt.label}</dt>
										<dd class="font-mono text-ink-800">{formatOptionValue(opt.value)}</dd>
									</div>
								{/each}
							</dl>
						{/if}
					</li>
				{/each}
			</ul>
		{/if}
	</section>

	<!-- Generated settings.toml -->
	<section class="rounded-lg border border-ink-200 bg-white shadow-sm">
		<header class="flex items-center justify-between border-b border-ink-200 px-6 py-4">
			<div>
				<h3 class="text-sm font-semibold tracking-[0.18em] text-navy-900 uppercase">
					Generated <code class="font-mono text-[11px] text-ink-700">house/settings.toml</code>
				</h3>
				<p class="mt-0.5 text-xs text-ink-500">
					What we'll hand to <code class="font-mono">tomllib</code> on the Python side. Side-by-side
					compatible with the file checked into the repo.
				</p>
			</div>
			<div class="flex gap-2">
				<button
					type="button"
					class="rounded-md border border-ink-200 bg-white px-3 py-1.5 text-xs font-medium text-ink-700 shadow-sm hover:bg-ink-50"
					onclick={() => copyToClipboard(settingsToml, 'settings.toml')}
				>
					{copyState.kind === 'copied' && copyState.key === 'settings.toml' ? 'Copied!' : 'Copy'}
				</button>
				<button
					type="button"
					class="rounded-md border border-ink-200 bg-white px-3 py-1.5 text-xs font-medium text-ink-700 shadow-sm hover:bg-ink-50"
					onclick={() => downloadText('settings.toml', 'application/toml', settingsToml)}
				>
					Download
				</button>
			</div>
		</header>
		<pre
			class="overflow-auto bg-navy-950 px-6 py-4 font-mono text-[11px] leading-relaxed text-ink-100"><code
				>{settingsToml}</code
			></pre>
	</section>

	<!-- Crosslinks preview (only when populated) -->
	{#if snapshot.crosslinks.length > 0}
		<section class="rounded-lg border border-ink-200 bg-white shadow-sm">
			<header class="flex items-baseline justify-between border-b border-ink-200 px-6 py-4">
				<div>
					<h3 class="text-sm font-semibold tracking-[0.18em] text-navy-900 uppercase">
						Cross-link substitutes
					</h3>
					<p class="mt-0.5 text-xs text-ink-500">
						Captured for export. The build-side cross-link generator ships in a follow-up.
					</p>
				</div>
				<span class="font-mono text-xs text-ink-500">{snapshot.crosslinks.length}</span>
			</header>
			<div class="overflow-x-auto">
				<table class="min-w-full divide-y divide-ink-200 text-sm">
					<thead class="bg-ink-50 text-[11px] font-semibold tracking-wider text-ink-500 uppercase">
						<tr>
							<th class="px-4 py-2 text-left">Primary</th>
							<th class="px-4 py-2 text-left">Substitute</th>
							<th class="px-4 py-2 text-left">Notes</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-ink-100">
						{#each snapshot.crosslinks as row (row.id)}
							<tr>
								<td class="px-4 py-2">
									<div class="font-mono text-xs text-ink-800">
										{row.primary_mpn || '—'}
									</div>
									<div class="text-[11px] text-ink-500">{row.primary_mfg || '—'}</div>
								</td>
								<td class="px-4 py-2">
									<div class="font-mono text-xs text-ink-800">
										{row.substitute_mpn || '—'}
									</div>
									<div class="text-[11px] text-ink-500">{row.substitute_mfg || '—'}</div>
								</td>
								<td class="px-4 py-2 text-xs text-ink-600">{row.notes || ''}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</section>
	{/if}

	<!-- Full configuration JSON -->
	<section class="rounded-lg border border-ink-200 bg-white shadow-sm">
		<header class="flex items-center justify-between border-b border-ink-200 px-6 py-4">
			<div>
				<h3 class="text-sm font-semibold tracking-[0.18em] text-navy-900 uppercase">
					Configuration JSON
				</h3>
				<p class="mt-0.5 text-xs text-ink-500">
					Exactly what gets passed to Python via <code class="font-mono">js.globalThis</code>.
				</p>
			</div>
			<div class="flex gap-2">
				<button
					type="button"
					class="rounded-md border border-ink-200 bg-white px-3 py-1.5 text-xs font-medium text-ink-700 shadow-sm hover:bg-ink-50"
					onclick={() => copyToClipboard(configJson, 'configuration.json')}
				>
					{copyState.kind === 'copied' && copyState.key === 'configuration.json'
						? 'Copied!'
						: 'Copy'}
				</button>
				<button
					type="button"
					class="rounded-md border border-ink-200 bg-white px-3 py-1.5 text-xs font-medium text-ink-700 shadow-sm hover:bg-ink-50"
					onclick={() =>
						downloadText('hlcl-configuration.json', 'application/json', configJson)}
				>
					Download
				</button>
			</div>
		</header>
		<pre
			class="max-h-96 overflow-auto bg-ink-50 px-6 py-4 font-mono text-[11px] leading-relaxed text-ink-800"><code
				>{configJson}</code
			></pre>
	</section>
</div>
