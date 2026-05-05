<script lang="ts">
	import JSZip from 'jszip';
	import { appState } from '$lib/state.svelte';
	import { consoleLog } from '$lib/console.svelte';
	import {
		cleanBuild,
		computeBuildStats,
		listBuildOutputs,
		readOutputBytes,
		runBuild,
		type BuildOutputFile
	} from '$lib/hlcl-runner';
	import { saveBlobAs } from '$lib/texapi';
	import { sanitizeConfigFilenameStem } from '$lib/config-filename';
	import SectionHeader from '../SectionHeader.svelte';

	type BuildStatus = 'idle' | 'running' | 'success' | 'error';
	let buildStatus = $state<BuildStatus>('idle');
	let buildOutputs = $state<BuildOutputFile[]>([]);
	let buildError = $state<string | null>(null);
	let zipping = $state(false);

	async function onRunBuild() {
		if (buildStatus === 'running') return;
		buildStatus = 'running';
		buildError = null;
		buildOutputs = [];
		const t0 = Date.now();
		// Snapshot the config we're handing to the build; we'll cache
		// the stats against THIS exact config (not the live one, which
		// the user might already be editing in another tab while the
		// build is running).
		const builtConfig = appState.snapshotConfig();
		try {
			await cleanBuild();
			await runBuild(builtConfig);
			buildOutputs = await listBuildOutputs();
			buildStatus = 'success';
			const dt = ((Date.now() - t0) / 1000).toFixed(1);
			consoleLog.system(`Build finished in ${dt}s. Produced ${buildOutputs.length} artifact(s).`);

			// Aggregate library-stats for the configure-page banner.
			// Failure here is non-fatal — the build itself succeeded —
			// so we surface it as an error log line and leave any prior
			// cached stats in place (they'll still flip to "stale" via
			// the config-hash check).
			try {
				const stats = await computeBuildStats();
				appState.setBuildStats(stats, builtConfig);
				consoleLog.system(
					`Library stats: ${stats.components.toLocaleString()} components · ` +
						`${stats.unique_footprints.toLocaleString()} unique footprints.`
				);
			} catch (err) {
				const msg = err instanceof Error ? err.message : String(err);
				consoleLog.error(`Library-stats aggregation failed: ${msg}`);
			}
		} catch (err) {
			buildError = err instanceof Error ? err.message : String(err);
			buildStatus = 'error';
			consoleLog.error(`Build failed: ${buildError}`);
		}
	}

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
			saveBlobAs(blob, file.path.replace(/\//g, '_'));
			consoleLog.info(`Downloaded ${file.path} (${formatBytes(file.size)}).`);
		} catch (err) {
			const msg = err instanceof Error ? err.message : String(err);
			consoleLog.error(`Failed to download ${file.path}: ${msg}`);
		}
	}

	async function downloadZip() {
		if (zipping || buildOutputs.length === 0) return;
		zipping = true;
		try {
			const zip = new JSZip();
			// Embed the canonical BuildConfig that produced these artifacts so
			// recipients can reproduce the run via the (future) CLI.
			zip.file('build-config.json', JSON.stringify(appState.snapshotConfig(), null, 2));
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

<SectionHeader title="Generate &amp; download" description="Run the build in your browser." />

<div class="mt-6 grid gap-6 lg:grid-cols-3">
	<div class="space-y-6 lg:col-span-2">
		<section class="rounded-lg border border-ink-200 bg-white p-6">
			<div class="flex flex-wrap items-start justify-between gap-3">
				<div>
					<h3 class="text-sm font-semibold tracking-wider text-navy-700 uppercase">Build</h3>
					<p class="mt-1 text-xs text-ink-500">
						Runs <code class="rounded bg-ink-100 px-1 py-0.5 font-mono">build.build_all()</code>
						against the source tree at
						<code class="rounded bg-ink-100 px-1 py-0.5 font-mono">/hlcl</code>
						in Pyodide. The first run downloads ~370&nbsp;KB of build inputs and installs
						<code class="rounded bg-ink-100 px-1 py-0.5 font-mono">xlwt</code> via micropip; later runs
						reuse the mounted tree.
					</p>
				</div>
				<span
					class={[
						'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold',
						buildStatus === 'success'
							? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200 ring-inset'
							: buildStatus === 'error'
								? 'bg-rose-50 text-rose-700 ring-1 ring-rose-200 ring-inset'
								: buildStatus === 'running'
									? 'bg-amber-50 text-amber-700 ring-1 ring-amber-200 ring-inset'
									: 'bg-ink-100 text-ink-600'
					]}
				>
					<span
						class={[
							'h-1.5 w-1.5 rounded-full',
							buildStatus === 'success'
								? 'bg-emerald-500'
								: buildStatus === 'error'
									? 'bg-rose-500'
									: buildStatus === 'running'
										? 'animate-pulse bg-amber-500'
										: 'bg-ink-400'
						]}
					></span>
					{buildStatus === 'idle'
						? 'Ready'
						: buildStatus === 'running'
							? 'Building…'
							: buildStatus === 'success'
								? `${buildOutputs.length} artifact${buildOutputs.length === 1 ? '' : 's'}`
								: 'Build failed'}
				</span>
			</div>

			<div class="mt-4 flex flex-wrap items-center gap-3">
				<button
					type="button"
					onclick={onRunBuild}
					disabled={buildStatus === 'running' || summary.enabled.length === 0}
					class="inline-flex items-center gap-2 rounded-md bg-navy-900 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-navy-800 disabled:cursor-not-allowed disabled:opacity-50"
				>
					{#if buildStatus === 'running'}
						<svg
							class="h-4 w-4 animate-spin"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
						>
							<path
								d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"
							/>
						</svg>
						Building in Pyodide…
					{:else}
						<svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
							<path
								fill-rule="evenodd"
								d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7.5a.5.5 0 01.8-.4l4 2.5a.5.5 0 010 .8l-4 2.5a.5.5 0 01-.8-.4v-5z"
								clip-rule="evenodd"
							/>
						</svg>
						Run build
					{/if}
				</button>

				{#if buildStatus === 'success' && buildOutputs.length > 0}
					<button
						type="button"
						onclick={downloadZip}
						disabled={zipping}
						class="inline-flex items-center gap-2 rounded-md bg-accent-500 px-4 py-2 text-sm font-semibold text-navy-950 shadow-sm transition hover:bg-accent-400 disabled:cursor-wait disabled:opacity-60"
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

				{#if buildError}
					<span class="text-xs text-rose-600">{buildError}</span>
				{/if}
			</div>

			{#if buildStatus === 'success' && buildOutputs.length > 0}
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
