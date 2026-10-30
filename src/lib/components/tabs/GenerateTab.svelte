<script lang="ts">
	import JSZip from 'jszip';
	import { tick } from 'svelte';
	import { autoBuild } from '$lib/auto-build.svelte';
	import { appState } from '$lib/state.svelte';
	import { consoleLog } from '$lib/console.svelte';
	import { readOutputBytes, type BuildOutputFile } from '$lib/hlcl-runner';
	import { saveBlobAs } from '$lib/texapi';
	import { sanitizeConfigFilenameStem } from '$lib/config-filename';
	import SectionHeader from '../SectionHeader.svelte';
	import WorkbookViewer from '../WorkbookViewer.svelte';

	// Builds run in the background (see `auto-build.svelte.ts`); this tab
	// shows their status and the artifacts of the last completed build.
	const buildOutputs = $derived(autoBuild.outputs);
	const liveConfig = $derived(appState.snapshotConfig());
	const upToDate = $derived(autoBuild.isCurrent(liveConfig));
	let zipping = $state(false);
	let viewingPath = $state<string | null>(null);
	let viewerAnchor = $state<HTMLElement | undefined>();

	// Close the viewer if a rebuild dropped the workbook it was showing.
	$effect(() => {
		if (viewingPath && !buildOutputs.some((f) => f.path === viewingPath)) viewingPath = null;
	});

	async function viewWorkbook(file: BuildOutputFile) {
		viewingPath = file.path;
		await tick();
		viewerAnchor?.scrollIntoView({ behavior: 'smooth', block: 'start' });
	}

	const status = $derived.by(() => {
		if (autoBuild.running) return { tone: 'amber', label: 'Building…' };
		if (autoBuild.queuedHash) return { tone: 'amber', label: 'Rebuild queued' };
		if (autoBuild.failedHash) return { tone: 'rose', label: 'Build failed' };
		if (upToDate)
			return {
				tone: 'emerald',
				label: `Up to date · ${buildOutputs.length} artifact${buildOutputs.length === 1 ? '' : 's'}`
			};
		return { tone: 'ink', label: appState.ui.auto_build ? 'Waiting…' : 'Out of date' };
	});

	function safeConfigName(): string {
		return sanitizeConfigFilenameStem(appState.ui.config_name || '');
	}

	function formatBytes(n: number): string {
		if (n < 1024) return `${n} B`;
		if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KiB`;
		return `${(n / 1024 / 1024).toFixed(2)} MiB`;
	}

	async function downloadIndividual(file: BuildOutputFile) {
		try {
			const bytes = await readOutputBytes(file.path);
			const blob = new Blob([bytes as BlobPart], { type: 'application/octet-stream' });
			// Save under the file's basename, not its full output-relative path.
			// The previous `path.replace(/\//g, '_')` produced names like
			// `standards_standards.tex` and `standards_example-footprint.png`,
			// which broke `\input{standards.tex}` / `\includegraphics{example-footprint}`
			// inside the populated standards.tex once the user dropped the
			// downloaded files next to each other on disk. Every output file
			// the build emits has a unique basename across the tree (vendors
			// are namespaced via `<mfg>-<family>`; everything in `standards/`
			// has a unique name), so there's no collision risk in flattening
			// to basename.
			const filename = file.path.split('/').pop() ?? file.path;
			saveBlobAs(blob, filename);
			consoleLog.info(`Downloaded ${file.path} (${formatBytes(file.size)}).`);
		} catch (err) {
			const msg = err instanceof Error ? err.message : String(err);
			consoleLog.error(`Failed to download ${file.path}: ${msg}`);
		}
	}

	async function downloadZip() {
		if (zipping || buildOutputs.length === 0 || !upToDate) return;
		zipping = true;
		try {
			const zip = new JSZip();
			// Embed the BuildConfig that produced these artifacts so
			// recipients can reproduce the run via the CLI.
			zip.file('build-config.json', JSON.stringify(autoBuild.builtConfig, null, 2));
			for (const f of buildOutputs) {
				const bytes = await readOutputBytes(f.path);
				zip.file(f.path, bytes);
			}
			const blob = await zip.generateAsync({ type: 'blob', compression: 'DEFLATE' });
			const filename = `${safeConfigName()}.zip`;
			saveBlobAs(blob, filename);
			consoleLog.info(
				`Packaged ${buildOutputs.length} artifact(s) + build-config.json into ${filename} (${formatBytes(blob.size)}).`
			);
		} catch (err) {
			const msg = err instanceof Error ? err.message : String(err);
			consoleLog.error(`Failed to build ZIP: ${msg}`);
		} finally {
			zipping = false;
		}
	}

	function downloadJson() {
		const cfg = appState.snapshotConfig();
		const data = JSON.stringify(cfg, null, 2);
		const blob = new Blob([data], { type: 'application/json' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		const filename = `${safeConfigName()}.json`;
		a.download = filename;
		document.body.appendChild(a);
		a.click();
		a.remove();
		URL.revokeObjectURL(url);
		consoleLog.info(`Downloaded ${filename}`);
	}

	/**
	 * Group the flat output list by top-level folder for display. Anything
	 * directly in `build/output/` lands in `'.'`; nested artifacts like
	 * `standards/standards.tex` end up under `'standards'`. Group keys are
	 * sorted; files within a group preserve the listBuildOutputs() ordering
	 * (path-sorted by Python).
	 */
	function groupByFolder(files: BuildOutputFile[]): { folder: string; files: BuildOutputFile[] }[] {
		const groups = new Map<string, BuildOutputFile[]>();
		for (const f of files) {
			const slash = f.path.indexOf('/');
			const folder = slash < 0 ? '.' : f.path.slice(0, slash);
			if (!groups.has(folder)) groups.set(folder, []);
			groups.get(folder)!.push(f);
		}
		return Array.from(groups.entries())
			.sort(([a], [b]) => (a === '.' ? -1 : b === '.' ? 1 : a.localeCompare(b)))
			.map(([folder, files]) => ({ folder, files }));
	}

	const outputGroups = $derived(groupByFolder(buildOutputs));
	const totalOutputBytes = $derived(buildOutputs.reduce((acc, f) => acc + f.size, 0));

	let summary = $derived({
		enabled: appState.enabledFamilyIds(),
		artifactsOn: Object.entries(appState.config.artifacts).filter(([, v]) => v).length,
		artifactsTotal: Object.keys(appState.config.artifacts).length,
		crosslinks: appState.config.crosslinks.length
	});
</script>

<SectionHeader
	title="Generate &amp; download"
	description="The library rebuilds in your browser whenever settings change."
/>

<div class="mt-6 grid gap-6 lg:grid-cols-3">
	<div class="space-y-6 lg:col-span-2">
		<section class="rounded-lg border border-ink-200 bg-white p-6">
			<div class="flex flex-wrap items-start justify-between gap-3">
				<div>
					<h3 class="text-sm font-semibold tracking-wider text-navy-700 uppercase">Build</h3>
					<p class="mt-1 text-xs text-ink-500">
						Runs <code class="rounded bg-ink-100 px-1 py-0.5 font-mono">build.build_all()</code>
						in a background Pyodide worker, so the page stays responsive. Each change rebuilds once your
						edits settle; changes made mid-build queue one follow-up build. The first build downloads
						Pyodide and the build inputs.
					</p>
				</div>
				<span
					class={[
						'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold ring-1 ring-inset',
						{
							emerald: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
							rose: 'bg-rose-50 text-rose-700 ring-rose-200',
							amber: 'bg-amber-50 text-amber-700 ring-amber-200',
							ink: 'bg-ink-100 text-ink-600 ring-ink-200'
						}[status.tone]
					]}
				>
					<span
						class={[
							'h-1.5 w-1.5 rounded-full',
							{
								emerald: 'bg-emerald-500',
								rose: 'bg-rose-500',
								amber: 'animate-pulse bg-amber-500',
								ink: 'bg-ink-400'
							}[status.tone]
						]}
					></span>
					{status.label}
				</span>
			</div>

			<div class="mt-4 flex flex-wrap items-center gap-3">
				<label class="inline-flex items-center gap-2 text-sm text-ink-700">
					<input
						type="checkbox"
						class="h-4 w-4 rounded border-ink-300 text-navy-700 focus:ring-navy-500"
						bind:checked={appState.ui.auto_build}
					/>
					Rebuild automatically
				</label>

				{#if !appState.ui.auto_build || autoBuild.failedHash}
					<button
						type="button"
						onclick={() => autoBuild.buildNow(appState.snapshotConfig())}
						disabled={autoBuild.running || upToDate}
						class="inline-flex items-center gap-2 rounded-md bg-navy-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-navy-800 disabled:cursor-not-allowed disabled:opacity-50"
					>
						{autoBuild.failedHash ? 'Retry build' : 'Build now'}
					</button>
				{/if}

				{#if buildOutputs.length > 0}
					<button
						type="button"
						onclick={downloadZip}
						disabled={zipping || !upToDate}
						title={upToDate ? undefined : 'Available once the build matches your current settings'}
						class="inline-flex items-center gap-2 rounded-md bg-accent-500 px-4 py-2 text-sm font-semibold text-navy-950 shadow-sm transition hover:bg-accent-400 disabled:cursor-not-allowed disabled:opacity-60"
					>
						{#if zipping}
							Zipping…
						{:else}
							<svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
								<path
									d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM10 3a1 1 0 011 1v6.586l1.293-1.293a1 1 0 011.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 011.414-1.414L9 10.586V4a1 1 0 011-1z"
								/>
							</svg>
							Download {safeConfigName()}.zip
						{/if}
					</button>
				{/if}

				{#if summary.enabled.length === 0}
					<span class="text-xs text-amber-700"
						>Enable at least one family on the Libraries tab first.</span
					>
				{/if}

				{#if autoBuild.error}
					<span class="text-xs text-rose-600">{autoBuild.error}</span>
				{/if}
			</div>

			{#if buildOutputs.length > 0 && !upToDate}
				<p class="mt-3 text-xs text-amber-700">
					These artifacts are from the previous build. Downloads unlock when the build matches your
					current settings.
				</p>
			{/if}

			{#if buildOutputs.length > 0}
				<div class="mt-5 border-t border-ink-200 pt-4">
					<div class="flex items-baseline justify-between">
						<h4 class="text-xs font-semibold tracking-wider text-navy-700 uppercase">
							Output artifacts
						</h4>
						<span class="font-mono text-[11px] text-ink-500">
							{buildOutputs.length} files · {formatBytes(totalOutputBytes)}
						</span>
					</div>
					<div class="mt-3 space-y-4">
						{#each outputGroups as group (group.folder)}
							<div>
								{#if group.folder !== '.'}
									<div class="mb-1 flex items-center gap-1.5 text-[11px] font-medium text-ink-500">
										<svg class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
											<path
												d="M2 6a2 2 0 012-2h3.93l1.4 1.4A2 2 0 0010.74 6H16a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"
											/>
										</svg>
										<span class="font-mono">{group.folder}/</span>
									</div>
								{/if}
								<ul
									class={[
										'divide-y divide-ink-100 rounded-md border border-ink-200 bg-white',
										group.folder !== '.' ? 'ml-4' : ''
									]}
								>
									{#each group.files as file (file.path)}
										<li class="flex items-center justify-between gap-3 px-3 py-2">
											<div class="min-w-0 flex-1">
												<div class="truncate font-mono text-xs text-ink-800">
													{file.path.split('/').slice(-1)[0]}
												</div>
												<div class="truncate font-mono text-[10px] text-ink-400">
													{file.path}
												</div>
											</div>
											<span class="shrink-0 font-mono text-[11px] text-ink-500">
												{formatBytes(file.size)}
											</span>
											{#if file.path.endsWith('.xls')}
												<button
													type="button"
													class={[
														'shrink-0 rounded p-1 hover:bg-navy-50 hover:text-navy-700',
														viewingPath === file.path ? 'text-navy-700' : 'text-ink-400'
													]}
													title="View columns and rows of {file.path}"
													aria-label="View {file.path}"
													onclick={() => viewWorkbook(file)}
												>
													<svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
														<path d="M10 12.5a2.5 2.5 0 100-5 2.5 2.5 0 000 5z" />
														<path
															fill-rule="evenodd"
															d="M.66 10.59a1.65 1.65 0 010-1.18C2.07 5.7 5.73 3 10 3s7.93 2.7 9.34 6.41c.15.38.15.8 0 1.18C17.93 14.3 14.27 17 10 17S2.07 14.3.66 10.59zM14 10a4 4 0 11-8 0 4 4 0 018 0z"
															clip-rule="evenodd"
														/>
													</svg>
												</button>
											{/if}
											<button
												type="button"
												class="shrink-0 rounded p-1 text-ink-400 hover:bg-navy-50 hover:text-navy-700"
												title="Download {file.path}"
												aria-label="Download {file.path}"
												onclick={() => downloadIndividual(file)}
											>
												<svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
													<path
														d="M10 3a1 1 0 011 1v6.586l1.293-1.293a1 1 0 011.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 011.414-1.414L9 10.586V4a1 1 0 011-1zM3 16a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z"
													/>
												</svg>
											</button>
										</li>
									{/each}
								</ul>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</section>

		<section class="rounded-lg border border-ink-200 bg-white p-6">
			<h3 class="text-sm font-semibold tracking-wider text-navy-700 uppercase">
				Configuration export
			</h3>
			<p class="mt-1 text-xs text-ink-500">
				Save your current configuration as JSON. Useful for sharing or version-controlling alongside
				your design.
			</p>
			<div class="mt-4 flex flex-wrap gap-3">
				<button
					type="button"
					onclick={downloadJson}
					class="inline-flex items-center gap-2 rounded-md bg-accent-500 px-4 py-2 text-sm font-semibold text-navy-950 shadow-sm transition hover:bg-accent-400"
				>
					<svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"
						><path
							d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM10 3a1 1 0 011 1v6.586l1.293-1.293a1 1 0 011.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 011.414-1.414L9 10.586V4a1 1 0 011-1z"
						/></svg
					>
					Download {safeConfigName()}.json
				</button>
			</div>
		</section>
	</div>

	<aside class="rounded-lg border border-ink-200 bg-white p-6">
		<h3 class="text-sm font-semibold tracking-wider text-navy-700 uppercase">Build summary</h3>
		<dl class="mt-4 space-y-3 text-sm">
			<div class="flex items-baseline justify-between">
				<dt class="text-ink-500">Families enabled</dt>
				<dd class="font-mono text-ink-900">{summary.enabled.length}</dd>
			</div>
			<div class="flex items-baseline justify-between">
				<dt class="text-ink-500">Build outputs</dt>
				<dd class="font-mono text-ink-900">
					{summary.artifactsOn} / {summary.artifactsTotal}
				</dd>
			</div>
			<div class="flex items-baseline justify-between">
				<dt class="text-ink-500">Cross-link rows</dt>
				<dd class="font-mono text-ink-900">{summary.crosslinks}</dd>
			</div>
		</dl>
		{#if summary.enabled.length > 0}
			<div class="mt-4 border-t border-ink-200 pt-4">
				<div class="text-xs font-medium text-ink-500">Will build:</div>
				<ul class="mt-2 space-y-1">
					{#each summary.enabled as id (id)}
						<li class="flex items-center gap-1.5 font-mono text-[11px] text-ink-700">
							<span class="h-1 w-1 rounded-full bg-emerald-500"></span>
							{id}
						</li>
					{/each}
				</ul>
			</div>
		{:else}
			<div class="mt-4 rounded border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
				Pick at least one family on the Libraries tab.
			</div>
		{/if}
	</aside>
</div>

{#if viewingPath}
	<div bind:this={viewerAnchor} class="mt-6 scroll-mt-24">
		<WorkbookViewer
			path={viewingPath}
			revision={autoBuild.revision}
			onclose={() => (viewingPath = null)}
		/>
	</div>
{/if}
