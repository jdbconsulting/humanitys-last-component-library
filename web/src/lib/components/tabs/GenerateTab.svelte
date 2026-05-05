<script lang="ts">
	import { appState } from '$lib/state.svelte';
	import { consoleLog } from '$lib/console.svelte';
	import { getPyodide, resetPyodide } from '$lib/pyodide';
	import { compileLaTeX, compileLaTeXFiles, downloadPdf, saveBlobAs, type TexapiCompiler } from '$lib/texapi';
	import SectionHeader from '../SectionHeader.svelte';

	let busy = $state(false);
	let pyodideReady = $state(false);
	let lastError = $state<string | null>(null);

	async function withPyodide(fn: (py: Awaited<ReturnType<typeof getPyodide>>) => Promise<void>) {
		if (busy) return;
		busy = true;
		lastError = null;
		try {
			const py = await getPyodide();
			pyodideReady = true;
			await fn(py);
		} catch (err) {
			const msg = err instanceof Error ? err.message : String(err);
			lastError = msg;
			consoleLog.error(msg);
		} finally {
			busy = false;
		}
	}

	async function loadRuntime() {
		await withPyodide(async (py) => {
			consoleLog.info(`Pyodide version reported: ${py.version}`);
		});
	}

	async function helloWorld() {
		await withPyodide(async (py) => {
			consoleLog.info('Running: print("Hello from Pyodide!")');
			await py.runPythonAsync('print("Hello from Pyodide!")');
		});
	}

	async function pythonInfo() {
		await withPyodide(async (py) => {
			consoleLog.info('Running: import sys, platform; print(...)');
			await py.runPythonAsync(`
import sys, platform
print(f"Python:   {sys.version.split()[0]}")
print(f"Platform: {platform.platform()}")
print(f"Impl:     {platform.python_implementation()}")
`);
		});
	}

	async function dumpConfig() {
		await withPyodide(async (py) => {
			const cfg = JSON.stringify(appState.snapshot(), null, 2);
			consoleLog.info('Loading current configuration into Python as `config`…');
			(globalThis as unknown as { __hlcl_config: string }).__hlcl_config = cfg;
			await py.runPythonAsync(`
from js import globalThis
import json
config = json.loads(globalThis.__hlcl_config)
print(f"Loaded config with {len(config['families'])} family entries.")
print(f"Enabled: {[k for k, v in config['families'].items() if v.get('enabled')]}")
print(f"Build emits {sum(1 for k, v in config['build'].items() if v)} of {len(config['build'])} artifacts.")
`);
		});
	}

	function downloadJson() {
		const snapshot = appState.snapshot();
		const data = JSON.stringify(snapshot, null, 2);
		const blob = new Blob([data], { type: 'application/json' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		// Sanitise the config name for use as a filename.
		const safeName = (appState.configName || 'hlcl-configuration')
			.toLowerCase()
			.replace(/[^a-z0-9]+/g, '-')
			.replace(/^-+|-+$/g, '');
		const filename = `${safeName}.json`;
		a.download = filename;
		document.body.appendChild(a);
		a.click();
		a.remove();
		URL.revokeObjectURL(url);
		consoleLog.info(`Downloaded ${filename}`);
	}

	function resetRuntime() {
		resetPyodide();
		pyodideReady = false;
		consoleLog.system('Pyodide runtime cache cleared. Next run reloads from the CDN.');
	}

	let summary = $derived({
		enabled: appState.enabledFamilyIds(),
		buildOptionsOn: Object.entries(appState.build).filter(([, v]) => v).length,
		buildOptionsTotal: Object.keys(appState.build).length,
		crosslinks: appState.crosslinks.length
	});

	// ── LaTeX → PDF (Texapi) ──────────────────────────────────────────────────
	type TexInputMode = 'paste' | 'file';
	let texMode = $state<TexInputMode>('paste');
	let texContent = $state('');
	let texFileInput = $state<HTMLInputElement | null>(null);
	let texFileName = $state('document.tex');
	/** Extra files (images, .sty, etc.) loaded from disk alongside the main .tex */
	let texExtraFiles = $state<{ name: string; blob: Blob }[]>([]);
	let texExtraInput = $state<HTMLInputElement | null>(null);
	let texCompiler = $state<TexapiCompiler>('pdflatex');
	let texBusy = $state(false);
	let texErrors = $state<string[]>([]);
	let texStatus = $state<'idle' | 'compiling' | 'success' | 'error'>('idle');

	const SAMPLE_TEX = `\\documentclass{article}
\\begin{document}
\\title{HLCL Component Library Standards}
\\maketitle
Hello from Humanity's Last Component Library!
\\end{document}`;

	async function compileLatex() {
		if (texBusy) return;
		texBusy = true;
		texStatus = 'compiling';
		texErrors = [];
		const outputName = texFileName.replace(/\.tex$/i, '') + '.pdf';
		consoleLog.info(`Texapi: compiling "${texFileName}" with ${texCompiler}…`);
		try {
			let result;
			if (texExtraFiles.length === 0) {
				// Simple path — single content string
				result = await compileLaTeX(texContent, texCompiler);
			} else {
				// Multi-file path
				const files: { name: string; content: string | Blob }[] = [
					{ name: texFileName, content: texContent },
					...texExtraFiles.map((f) => ({ name: f.name, content: f.blob }))
				];
				result = await compileLaTeXFiles(files, texFileName, texCompiler);
			}

			if (result.status === 'success' && result.resultPath) {
				consoleLog.info(`Texapi: compilation succeeded. Downloading ${outputName}…`);
				const pdfBlob = await downloadPdf(result.resultPath);
				saveBlobAs(pdfBlob, outputName);
				consoleLog.info(`Downloaded ${outputName} (${(pdfBlob.size / 1024).toFixed(1)} KB)`);
				texStatus = 'success';
			} else {
				texErrors = result.errors ?? ['Unknown compilation error.'];
				texStatus = 'error';
				for (const e of texErrors) consoleLog.error(`Texapi: ${e}`);
			}
		} catch (err) {
			const msg = err instanceof Error ? err.message : String(err);
			texErrors = [msg];
			texStatus = 'error';
			consoleLog.error(`Texapi: ${msg}`);
		} finally {
			texBusy = false;
		}
	}

	function onTexFileChange(e: Event) {
		const file = (e.target as HTMLInputElement).files?.[0];
		if (!file) return;
		texFileName = file.name;
		const reader = new FileReader();
		reader.onload = (ev) => { texContent = ev.target?.result as string; };
		reader.readAsText(file);
	}

	function onExtraFilesChange(e: Event) {
		const incoming = Array.from((e.target as HTMLInputElement).files ?? []);
		for (const f of incoming) {
			if (!texExtraFiles.some((x) => x.name === f.name)) {
				texExtraFiles = [...texExtraFiles, { name: f.name, blob: f }];
			}
		}
		if (texExtraInput) texExtraInput.value = '';
	}

	function removeExtraFile(name: string) {
		texExtraFiles = texExtraFiles.filter((f) => f.name !== name);
	}
</script>

<SectionHeader
	title="Generate &amp; download"
	description="Run the build in your browser. The first run downloads Pyodide (~10 MB) from the jsdelivr CDN; afterwards it stays cached. Watch the console for stdout/stderr."
/>

<div class="mt-6 grid gap-6 lg:grid-cols-3">
	<div class="space-y-6 lg:col-span-2">
		<section class="rounded-lg border border-ink-200 bg-white p-6">
			<h3 class="text-sm font-semibold tracking-wider text-navy-700 uppercase">Pyodide runtime</h3>
			<p class="mt-1 text-xs text-ink-500">
				These buttons exist to prove the Python pipeline is wired end-to-end while we port the rest
				of the build over.
			</p>

			<div class="mt-4 grid gap-3 sm:grid-cols-2">
				<button
					type="button"
					class="flex items-center justify-between rounded-md border border-ink-200 bg-white px-4 py-3 text-left text-sm font-medium text-ink-800 shadow-sm transition hover:border-navy-400 hover:bg-navy-50/50 disabled:cursor-wait disabled:opacity-60"
					onclick={loadRuntime}
					disabled={busy}
				>
					<span>
						<span class="block">Load Pyodide</span>
						<span class="text-xs font-normal text-ink-500">First time downloads from CDN</span>
					</span>
					<span class="ml-3 text-lg leading-none text-navy-600">→</span>
				</button>

				<button
					type="button"
					class="flex items-center justify-between rounded-md border border-ink-200 bg-white px-4 py-3 text-left text-sm font-medium text-ink-800 shadow-sm transition hover:border-navy-400 hover:bg-navy-50/50 disabled:cursor-wait disabled:opacity-60"
					onclick={helloWorld}
					disabled={busy}
				>
					<span>
						<span class="block">print("Hello, world!")</span>
						<span class="text-xs font-normal text-ink-500">Smoke-test stdout</span>
					</span>
					<span class="ml-3 text-lg leading-none text-navy-600">→</span>
				</button>

				<button
					type="button"
					class="flex items-center justify-between rounded-md border border-ink-200 bg-white px-4 py-3 text-left text-sm font-medium text-ink-800 shadow-sm transition hover:border-navy-400 hover:bg-navy-50/50 disabled:cursor-wait disabled:opacity-60"
					onclick={pythonInfo}
					disabled={busy}
				>
					<span>
						<span class="block">Print sys / platform</span>
						<span class="text-xs font-normal text-ink-500">Confirm runtime version</span>
					</span>
					<span class="ml-3 text-lg leading-none text-navy-600">→</span>
				</button>

				<button
					type="button"
					class="flex items-center justify-between rounded-md border border-ink-200 bg-white px-4 py-3 text-left text-sm font-medium text-ink-800 shadow-sm transition hover:border-navy-400 hover:bg-navy-50/50 disabled:cursor-wait disabled:opacity-60"
					onclick={dumpConfig}
					disabled={busy}
				>
					<span>
						<span class="block">Pass config to Python</span>
						<span class="text-xs font-normal text-ink-500">Cross-boundary smoke-test</span>
					</span>
					<span class="ml-3 text-lg leading-none text-navy-600">→</span>
				</button>
			</div>

			<div class="mt-5 flex items-center gap-3 text-xs text-ink-500">
				<span
					class={[
						'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 font-medium',
						pyodideReady
							? 'bg-emerald-50 text-emerald-700'
							: busy
								? 'bg-amber-50 text-amber-700'
								: 'bg-ink-100 text-ink-600'
					]}
				>
					<span
						class={[
							'h-1.5 w-1.5 rounded-full',
							pyodideReady ? 'bg-emerald-500' : busy ? 'animate-pulse bg-amber-500' : 'bg-ink-400'
						]}
					></span>
					{pyodideReady ? 'Runtime ready' : busy ? 'Loading…' : 'Runtime not loaded'}
				</span>
				<button
					type="button"
					class="text-ink-500 underline-offset-2 hover:text-ink-800 hover:underline"
					onclick={resetRuntime}
					disabled={busy}
				>
					Reset cache
				</button>
				{#if lastError}
					<span class="text-rose-600">{lastError}</span>
				{/if}
			</div>
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
					Download configuration.json
				</button>
				<button
					type="button"
					class="inline-flex items-center gap-2 rounded-md border border-ink-200 bg-white px-4 py-2 text-sm font-semibold text-ink-700 shadow-sm hover:bg-ink-50"
					onclick={() => appState.resetAll()}
				>
					Reset to defaults
				</button>
			</div>
		</section>

		<!-- LaTeX → PDF via Texapi -->
		<section class="rounded-lg border border-ink-200 bg-white p-6">
			<div class="flex flex-wrap items-start justify-between gap-3">
				<div>
					<h3 class="text-sm font-semibold tracking-wider text-navy-700 uppercase">
						LaTeX → PDF
					</h3>
					<p class="mt-1 text-xs text-ink-500">
						Compile a <code class="rounded bg-ink-100 px-1 py-0.5 font-mono">.tex</code> document to PDF via
						<a
							href="https://texapi.ovh"
							target="_blank"
							rel="noopener noreferrer"
							class="text-navy-600 underline-offset-2 hover:underline"
						>Texapi</a>. Paste content or upload a file. Extra assets (images, <code class="rounded bg-ink-100 px-1 py-0.5 font-mono">.sty</code>) can be attached below.
					</p>
				</div>
				<!-- Status pill -->
				<span class={[
					'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold',
					texStatus === 'success'
						? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200 ring-inset'
						: texStatus === 'error'
							? 'bg-rose-50 text-rose-700 ring-1 ring-rose-200 ring-inset'
							: texStatus === 'compiling'
								? 'bg-amber-50 text-amber-700 ring-1 ring-amber-200 ring-inset'
								: 'bg-ink-100 text-ink-600'
				]}>
					<span class={[
						'h-1.5 w-1.5 rounded-full',
						texStatus === 'success' ? 'bg-emerald-500'
						: texStatus === 'error' ? 'bg-rose-500'
						: texStatus === 'compiling' ? 'animate-pulse bg-amber-500'
						: 'bg-ink-400'
					]}></span>
					{texStatus === 'idle' ? 'Ready' : texStatus === 'compiling' ? 'Compiling…' : texStatus === 'success' ? 'PDF downloaded' : 'Compile error'}
				</span>
			</div>

			<!-- Input mode toggle -->
			<div class="mt-4 flex gap-1 rounded-lg border border-ink-200 bg-ink-50 p-1 text-sm w-fit">
				{#each (['paste', 'file'] as TexInputMode[]) as mode (mode)}
					<button
						type="button"
						onclick={() => { texMode = mode; texStatus = 'idle'; }}
						class={[
							'rounded-md px-3 py-1.5 text-xs font-medium transition',
							texMode === mode ? 'bg-white text-ink-900 shadow-sm' : 'text-ink-500 hover:text-ink-800'
						]}
					>
						{mode === 'paste' ? 'Paste / type' : 'Upload .tex'}
					</button>
				{/each}
			</div>

			{#if texMode === 'paste'}
				<!-- Paste / type mode -->
				<div class="mt-3 space-y-2">
					<div class="flex items-center justify-between">
						<label class="text-xs font-medium text-ink-700" for="tex-filename">Filename</label>
						<button
							type="button"
							class="text-[11px] text-ink-400 underline-offset-2 hover:text-navy-700 hover:underline"
							onclick={() => { texContent = SAMPLE_TEX; texFileName = 'document.tex'; }}
						>
							Load sample
						</button>
					</div>
					<input
						id="tex-filename"
						type="text"
						bind:value={texFileName}
						placeholder="document.tex"
						class="w-full rounded-md border border-ink-200 bg-white px-3 py-1.5 font-mono text-xs text-ink-800 shadow-sm focus:border-navy-400 focus:ring-1 focus:ring-navy-400 focus:outline-none"
					/>
					<textarea
						bind:value={texContent}
						placeholder="Paste your LaTeX source here…"
						rows={14}
						class="w-full rounded-md border border-ink-200 bg-ink-50 px-3 py-2 font-mono text-xs text-ink-800 shadow-sm focus:border-navy-400 focus:ring-1 focus:ring-navy-400 focus:outline-none"
					></textarea>
				</div>
			{:else}
				<!-- Upload mode -->
				<input
					bind:this={texFileInput}
					type="file"
					accept=".tex,text/plain"
					class="sr-only"
					onchange={onTexFileChange}
				/>
				<button
					type="button"
					class="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border-2 border-dashed border-ink-300 px-6 py-8 text-sm text-ink-500 transition hover:border-navy-400 hover:text-navy-700"
					onclick={() => texFileInput?.click()}
				>
					<svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
						<path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clip-rule="evenodd" />
					</svg>
					{texContent ? `Loaded: ${texFileName}` : 'Click to upload a .tex file'}
				</button>
			{/if}

			<!-- Extra asset files -->
			<div class="mt-4">
				<div class="flex items-center justify-between">
					<span class="text-xs font-medium text-ink-700">Extra assets</span>
					<button
						type="button"
						class="text-[11px] text-navy-600 underline-offset-2 hover:underline"
						onclick={() => texExtraInput?.click()}
					>
						+ Add files
					</button>
				</div>
				<input
					bind:this={texExtraInput}
					type="file"
					multiple
					class="sr-only"
					onchange={onExtraFilesChange}
				/>
				{#if texExtraFiles.length > 0}
					<ul class="mt-2 flex flex-wrap gap-2">
						{#each texExtraFiles as f (f.name)}
							<li class="flex items-center gap-1.5 rounded-full border border-ink-200 bg-ink-50 px-2.5 py-1 font-mono text-[11px] text-ink-700">
								{f.name}
								<button
									type="button"
									onclick={() => removeExtraFile(f.name)}
									class="ml-0.5 text-ink-400 hover:text-rose-600"
									aria-label="Remove {f.name}"
								>×</button>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="mt-1.5 text-[11px] text-ink-400">None — only needed for images, custom styles, fonts, etc.</p>
				{/if}
			</div>

			<!-- Compiler + compile button -->
			<div class="mt-5 flex flex-wrap items-center gap-3">
				<div class="flex items-center gap-2">
					<label class="text-xs font-medium text-ink-700" for="tex-compiler">Compiler</label>
					<select
						id="tex-compiler"
						bind:value={texCompiler}
						class="rounded-md border border-ink-200 bg-white px-2 py-1.5 text-xs font-medium text-ink-800 shadow-sm focus:border-navy-400 focus:ring-1 focus:ring-navy-400 focus:outline-none"
					>
						<option value="pdflatex">pdflatex</option>
						<option value="xelatex">xelatex</option>
						<option value="lualatex">lualatex</option>
					</select>
				</div>
				<button
					type="button"
					onclick={compileLatex}
					disabled={texBusy || !texContent.trim()}
					class="inline-flex items-center gap-2 rounded-md bg-navy-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-navy-800 disabled:cursor-not-allowed disabled:opacity-50"
				>
					{#if texBusy}
						<svg class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
						</svg>
						Compiling…
					{:else}
						<svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
							<path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM10 3a1 1 0 011 1v6.586l1.293-1.293a1 1 0 011.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 011.414-1.414L9 10.586V4a1 1 0 011-1z" clip-rule="evenodd" />
						</svg>
						Compile → PDF
					{/if}
				</button>
			</div>

			<!-- Compile errors -->
			{#if texErrors.length > 0}
				<div class="mt-4 rounded-md border border-rose-200 bg-rose-50 p-3">
					<p class="mb-2 text-xs font-semibold text-rose-800">Compilation errors:</p>
					<pre class="overflow-x-auto text-[11px] leading-relaxed text-rose-700 whitespace-pre-wrap">{texErrors.join('\n')}</pre>
				</div>
			{/if}
		</section>

		<section
			class="rounded-lg border border-dashed border-ink-300 bg-ink-50/60 p-6 text-sm text-ink-600"
		>
			<h3 class="text-sm font-semibold tracking-wider text-ink-700 uppercase">Coming soon</h3>
			<p class="mt-2">
				The full build pipeline (vendor .xls → footprints JSON → STEP → .PcbLib → zip) will run
				inside Pyodide as we port each stage off Make. The buttons above prove the bridge works; the
				rest is mechanical.
			</p>
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
					{summary.buildOptionsOn} / {summary.buildOptionsTotal}
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
