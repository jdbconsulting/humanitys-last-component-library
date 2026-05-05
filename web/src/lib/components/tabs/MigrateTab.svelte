<script lang="ts">
	import { base } from '$app/paths';
	import SectionHeader from '../SectionHeader.svelte';

	const PAS_URL = `${base}/scripts/relink_workspace_footprint.pas`;
	const PRJSCR_URL = `${base}/scripts/relink_workspace_footprint.PrjScr`;

	let openTrouble = $state<string | null>(null);

	const troubleItems: { id: string; q: string; a: string }[] = [
		{
			id: 'empty-dialog',
			q: 'Run Script… dialog is empty / can\'t find ReplaceManagedFootprints',
			a: 'The .pas file isn\'t part of an open script project. Open relink_workspace_footprint.PrjScr (File → Open) and try again.'
		},
		{
			id: 'nothing-happens',
			q: 'I clicked ReplaceManagedFootprints and nothing happened — no banner, no error',
			a: 'Altium is running a cached compilation of an older .pas. As a sanity check, run the no-arg HelloWorld procedure from the same picker. If HelloWorld also doesn\'t pop a dialog, close the project from the Projects panel, then File → Open it again. If HelloWorld fires but ReplaceManagedFootprints still doesn\'t, that\'s a real bug — capture the exact picker dialog state and report it. The diagnostic banner "ReplaceManagedFootprints v4 starting…" is the canary: if you see it, the latest .pas is loaded.'
		},
		{
			id: 'not-pcblib',
			q: '"Focused document is not a PcbLib"',
			a: 'Click the Footprint Library [Footprints] (N) tab to give it focus before running the script.'
		},
		{
			id: 'name-fail',
			q: '"Cannot proceed — name resolution failed" with a list of names',
			a: 'Either those footprint names don\'t exist in house.PcbLib (run python build.py house-pcblib or python build.py all to regenerate), or your selection contains the same PCC item from two different Workspace folders (deselect one).'
		},
		{
			id: 'no-source',
			q: '"Could not find a source PcbLib"',
			a: 'Open build/output/house.PcbLib in Altium (File → Open) so that exactly one non-target PcbLib is open, then re-run.'
		},
		{
			id: 'ambiguous-source',
			q: '"More than one PcbLib … is currently open"',
			a: 'Close all open PcbLib files except house.PcbLib so the script can unambiguously identify the source library, then re-run.'
		}
	];
</script>

<SectionHeader
	title="Migrate to Altium"
	description="Instructions for importing the generated library into an Altium Workspace and keeping managed footprints up to date when the library is regenerated."
/>

<!-- Two-column layout: import guide on the left, script download card on the right -->
<div class="mt-6 grid gap-6 lg:grid-cols-[1fr_320px]">

	<!-- ── Left column: workflow instructions ──────────────────────────── -->
	<div class="space-y-6">

		<!-- Initial import -->
		<section class="rounded-lg border border-ink-200 bg-white p-6">
			<h3 class="flex items-center gap-2 text-sm font-semibold tracking-wider text-navy-700 uppercase">
				<span class="flex h-5 w-5 items-center justify-center rounded-full bg-navy-900 text-[10px] font-bold text-white">1</span>
				First-time import
			</h3>
			<p class="mt-3 text-sm text-ink-700">
				After generating the library for the first time, add the
				<code class="rounded bg-ink-100 px-1 py-0.5 font-mono text-xs">.DbLib</code>
				files to your Altium project using the Library Importer:
			</p>
			<ol class="mt-3 space-y-2 text-sm text-ink-700">
				{#each [
					'In Altium Designer, open the Library Importer (Tools → Library Migrator, or from the Components panel).',
					'Add all .DbLib files from build/output/ as sources.',
					'Choose the target Workspace folder and follow the wizard.',
					'Altium creates managed component items and uploads them to the Workspace.'
				] as step, i (i)}
					<li class="flex items-start gap-3">
						<span class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent-100 text-[10px] font-semibold text-accent-800">{i + 1}</span>
						<span>{step}</span>
					</li>
				{/each}
			</ol>
			<div class="mt-4 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800">
				<strong class="font-semibold">Do not re-run Library Importer on subsequent builds.</strong>
				Library Importer has no "match existing" path — it will create duplicates instead of
				updating the items already in your Workspace.
				Use the DelphiScript workflow below for all subsequent updates.
			</div>
		</section>

		<!-- Updating footprints -->
		<section class="rounded-lg border border-ink-200 bg-white p-6">
			<h3 class="flex items-center gap-2 text-sm font-semibold tracking-wider text-navy-700 uppercase">
				<span class="flex h-5 w-5 items-center justify-center rounded-full bg-navy-900 text-[10px] font-bold text-white">2</span>
				Updating managed footprints
			</h3>
			<p class="mt-3 text-sm text-ink-700">
				The <code class="rounded bg-ink-100 px-1 py-0.5 font-mono text-xs">relink_workspace_footprint.pas</code>
				script walks every footprint in the focused multi-component PcbLib editor and replaces its
				geometry (all 2D/3D primitives, Description, Height) with the same-named footprint from the
				other open PcbLib (<code class="rounded bg-ink-100 px-1 py-0.5 font-mono text-xs">house.PcbLib</code>).
				The footprint <strong>Name</strong> and all managed-item metadata (Item Revision, Source,
				Revision State) are preserved — Altium owns those.
			</p>

			<div class="mt-5">
				<h4 class="text-xs font-semibold tracking-wider text-ink-600 uppercase">One-time setup</h4>
				<ol class="mt-2 space-y-2 text-sm text-ink-700">
					{#each [
						{ step: 'File → Open → relink_workspace_footprint.PrjScr (loads the script project; appears in the Projects panel). Note: opening the bare .pas via File → Open won\'t enumerate its procedures in the Run Script dialog — the .PrjScr is required.', code: null },
						{ step: 'File → Open → build/output/house.PcbLib (the source library, must stay open during the run). The script auto-detects it — no path constant to edit.', code: null }
					] as item, i (i)}
						<li class="flex items-start gap-3">
							<span class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-ink-100 text-[10px] font-semibold text-ink-600">{i + 1}</span>
							<div>
								<span>{item.step}</span>
								{#if item.code}
									<pre class="mt-1.5 overflow-x-auto rounded bg-ink-900 px-3 py-2 font-mono text-[11px] text-emerald-400">{item.code}</pre>
								{/if}
							</div>
						</li>
					{/each}
				</ol>
			</div>

			<div class="mt-6">
				<h4 class="text-xs font-semibold tracking-wider text-ink-600 uppercase">Per-batch workflow (repeat after each build)</h4>
				<ol class="mt-2 space-y-2 text-sm text-ink-700">
					{#each [
						'Components / Explorer panel → multi-select the PCC items you want to refresh (Ctrl-click / Shift-click) → right-click → Edit. Altium opens a single "Footprint Library [Footprints] (N)" tab. Click that tab so it\'s the focused document.',
						'File → Run Script… → in the Select Item to Run dialog, pick ReplaceManagedFootprints from relink_workspace_footprint.pas. The script inventories both libraries, pre-flights every name and bails out with a full error list on any mismatch, then replaces every target footprint\'s primitives and ends with a confirmation dialog.',
						'Visually verify the geometry against the source.',
						'Ctrl+S to save the Footprint Library tab.',
						'In the Projects panel, right-click the project → Save to Server. In the Edit Revision dialog, leave ✓ Update items related to enabled. Every PCC item in the batch gets a new revision, and every Workspace Component that references one of them auto-bumps (no manual relink on the CMP side).'
					] as step, i (i)}
						<li class="flex items-start gap-3">
							<span class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent-100 text-[10px] font-semibold text-accent-800">{i + 1}</span>
							<span>{step}</span>
						</li>
					{/each}
				</ol>
				<p class="mt-3 text-xs text-ink-500">
					Realistic batch size: 50–200 items per pass. For the 33 items in
					<code class="rounded bg-ink-100 px-1">pcc_link_map.csv</code> it's a single batch.
					Altium will get unhappy if you try to Edit thousands of items at once.
				</p>
			</div>
		</section>

		<!-- Matching rules -->
		<section class="rounded-lg border border-ink-200 bg-white p-6">
			<h3 class="text-sm font-semibold tracking-wider text-navy-700 uppercase">Matching rules</h3>
			<p class="mt-2 text-xs text-ink-600">
				For each footprint in the focused (target) library, the script looks up the footprint of
				the same name (case-insensitive) in <code class="rounded bg-ink-100 px-1">house.PcbLib</code>.
			</p>
			<table class="mt-4 w-full text-sm">
				<thead>
					<tr class="border-b border-ink-200">
						<th class="pb-2 text-left text-xs font-semibold text-ink-500">Matches in house.PcbLib</th>
						<th class="pb-2 text-left text-xs font-semibold text-ink-500">Action</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-ink-100">
					<tr>
						<td class="py-2.5 font-mono text-xs font-medium text-rose-700">0</td>
						<td class="py-2.5 text-xs text-ink-700"><strong class="text-rose-700">Error</strong> — fail fast. Can't refresh what isn't there.</td>
					</tr>
					<tr>
						<td class="py-2.5 font-mono text-xs font-medium text-emerald-700">1</td>
						<td class="py-2.5 text-xs text-ink-700">Replace target's primitives + Description/Height with source's.</td>
					</tr>
					<tr>
						<td class="py-2.5 font-mono text-xs font-medium text-rose-700">2+</td>
						<td class="py-2.5 text-xs text-ink-700"><strong class="text-rose-700">Error</strong> — <code class="rounded bg-ink-100 px-1">house.PcbLib</code> is supposed to have unique names.</td>
					</tr>
				</tbody>
			</table>
			<p class="mt-3 text-xs text-ink-500">
				Source footprints with no target counterpart are silently skipped. The script collects
				<em>all</em> name-resolution problems in a single pre-flight pass before mutating
				anything — the run either updates every target or none of them.
			</p>
		</section>

		<!-- Troubleshooting -->
		<section class="rounded-lg border border-ink-200 bg-white p-6">
			<h3 class="text-sm font-semibold tracking-wider text-navy-700 uppercase">Troubleshooting</h3>
			<ul class="mt-3 divide-y divide-ink-100">
				{#each troubleItems as item (item.id)}
					<li>
						<button
							type="button"
							class="flex w-full items-start justify-between gap-4 py-3 text-left"
							onclick={() => openTrouble = openTrouble === item.id ? null : item.id}
							aria-expanded={openTrouble === item.id}
						>
							<span class="text-sm font-medium text-ink-800">{item.q}</span>
							<svg
								class={['h-4 w-4 shrink-0 mt-0.5 text-ink-400 transition-transform', openTrouble === item.id ? 'rotate-180' : '']}
								viewBox="0 0 20 20"
								fill="currentColor"
							>
								<path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
							</svg>
						</button>
						{#if openTrouble === item.id}
							<p class="pb-3 text-sm text-ink-600">{item.a}</p>
						{/if}
					</li>
				{/each}
			</ul>
		</section>

	</div>

	<!-- ── Right column: script download card (sticky) ─────────────────── -->
	<aside class="space-y-4">
		<div class="sticky top-6 rounded-lg border border-navy-200 bg-navy-50 p-5 shadow-sm">
			<h3 class="text-sm font-semibold text-navy-900">DelphiScript download</h3>
			<p class="mt-1 text-xs text-ink-600">
				Both files must be downloaded together. Open the
				<code class="rounded bg-white/60 px-1 py-0.5 font-mono">.PrjScr</code>
				first — Altium's Run Script dialog only enumerates procedures from
				<code class="rounded bg-white/60 px-1 py-0.5 font-mono">.pas</code>
				files that are members of an open script project.
			</p>
			<div class="mt-4 flex flex-col gap-2">
				<a
					href={PAS_URL}
					download="relink_workspace_footprint.pas"
					class="flex items-center gap-3 rounded-md border border-navy-200 bg-white px-4 py-3 text-sm font-medium text-navy-900 shadow-sm transition hover:border-navy-400 hover:bg-navy-50"
				>
					<svg class="h-5 w-5 shrink-0 text-navy-600" viewBox="0 0 20 20" fill="currentColor">
						<path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM10 3a1 1 0 011 1v6.586l1.293-1.293a1 1 0 011.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 011.414-1.414L9 10.586V4a1 1 0 011-1z" clip-rule="evenodd" />
					</svg>
					<div class="min-w-0">
						<div class="truncate font-mono text-xs">relink_workspace_footprint.pas</div>
						<div class="text-[11px] text-ink-500">Script source (DelphiScript)</div>
					</div>
				</a>
				<a
					href={PRJSCR_URL}
					download="relink_workspace_footprint.PrjScr"
					class="flex items-center gap-3 rounded-md border border-navy-200 bg-white px-4 py-3 text-sm font-medium text-navy-900 shadow-sm transition hover:border-navy-400 hover:bg-navy-50"
				>
					<svg class="h-5 w-5 shrink-0 text-navy-600" viewBox="0 0 20 20" fill="currentColor">
						<path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM10 3a1 1 0 011 1v6.586l1.293-1.293a1 1 0 011.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 011.414-1.414L9 10.586V4a1 1 0 011-1z" clip-rule="evenodd" />
					</svg>
					<div class="min-w-0">
						<div class="truncate font-mono text-xs">relink_workspace_footprint.PrjScr</div>
						<div class="text-[11px] text-ink-500">Script project (required wrapper)</div>
					</div>
				</a>
			</div>

			<div class="mt-5 border-t border-navy-200 pt-4">
				<h4 class="text-xs font-semibold text-ink-600 uppercase tracking-wider">What gets replaced</h4>
				<ul class="mt-2 space-y-1 text-xs text-ink-700">
					{#each ['All 2D/3D primitives — pads, tracks, arcs, regions, fills, text, 3D bodies (with embedded STEP)', 'Footprint-level Description and Height'] as item (item)}
						<li class="flex items-start gap-1.5">
							<svg class="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-500" viewBox="0 0 20 20" fill="currentColor">
								<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
							</svg>
							{item}
						</li>
					{/each}
				</ul>
				<h4 class="mt-3 text-xs font-semibold text-ink-600 uppercase tracking-wider">Left alone</h4>
				<ul class="mt-2 space-y-1 text-xs text-ink-700">
					{#each ['Footprint Name (preserves managed-item identity)', 'Item Revision, Source, Revision Details, Revision State'] as item (item)}
						<li class="flex items-start gap-1.5">
							<svg class="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-400" viewBox="0 0 20 20" fill="currentColor">
								<path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
							</svg>
							{item}
						</li>
					{/each}
				</ul>
			</div>
		</div>
	</aside>

</div>
