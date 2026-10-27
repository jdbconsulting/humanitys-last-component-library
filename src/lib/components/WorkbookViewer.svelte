<script lang="ts">
	import { readWorkbook, type WorkbookSheet } from '$lib/hlcl-runner';

	let { path, onclose }: { path: string; onclose: () => void } = $props();

	const PAGE_SIZE = 50;

	let sheets = $state<WorkbookSheet[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let sheetIndex = $state(0);
	let view = $state<'rows' | 'columns'>('rows');
	let query = $state('');
	let pageIndex = $state(0);

	$effect(() => {
		const target = path;
		loading = true;
		error = null;
		sheets = [];
		sheetIndex = 0;
		query = '';
		pageIndex = 0;
		readWorkbook(target)
			.then((result) => {
				if (target === path) sheets = result;
			})
			.catch((err) => {
				if (target === path) error = err instanceof Error ? err.message : String(err);
			})
			.finally(() => {
				if (target === path) loading = false;
			});
	});

	const sheet = $derived(sheets[sheetIndex]);

	// The database standard requires ASCII in every field; flag anything else.
	function nonAscii(value: string): boolean {
		for (let i = 0; i < value.length; i++) if (value.charCodeAt(i) > 127) return true;
		return false;
	}

	function columnLetter(index: number): string {
		let out = '';
		for (let n = index + 1; n > 0; n = Math.floor((n - 1) / 26)) {
			out = String.fromCharCode(65 + ((n - 1) % 26)) + out;
		}
		return out;
	}

	// Spreadsheet row numbers: the header is row 1, so data starts at 2.
	const filtered = $derived.by(() => {
		if (!sheet) return [];
		const rows = sheet.rows.map((cells, i) => ({ number: i + 2, cells }));
		const q = query.trim().toLowerCase();
		return q ? rows.filter((r) => r.cells.some((c) => c.toLowerCase().includes(q))) : rows;
	});
	const pageCount = $derived(Math.max(1, Math.ceil(filtered.length / PAGE_SIZE)));
	const pageRows = $derived(filtered.slice(pageIndex * PAGE_SIZE, (pageIndex + 1) * PAGE_SIZE));

	const columns = $derived.by(() => {
		if (!sheet) return [];
		return sheet.headers.map((name, c) => {
			const filled = sheet.rows.map((r) => r[c] ?? '').filter((v) => v !== '');
			const distinct = [...new Set(filled)];
			return {
				letter: columnLetter(c),
				name,
				filled: filled.length,
				distinct: distinct.length,
				nonAscii: filled.filter(nonAscii).length,
				samples: distinct.slice(0, 3)
			};
		});
	});
	const nonAsciiTotal = $derived(columns.reduce((n, c) => n + c.nonAscii, 0));

	function setQuery(value: string) {
		query = value;
		pageIndex = 0;
	}

	const tabClass = (active: boolean) =>
		[
			'rounded-md px-3 py-1.5 text-xs font-semibold transition',
			active ? 'bg-navy-900 text-white' : 'text-ink-600 hover:bg-ink-100'
		].join(' ');
</script>

<section class="rounded-lg border border-ink-200 bg-white" aria-label="Workbook viewer">
	<header
		class="flex flex-wrap items-start justify-between gap-3 border-b border-ink-200 px-6 py-4"
	>
		<div class="min-w-0">
			<h3 class="text-sm font-semibold tracking-wider text-navy-700 uppercase">Workbook viewer</h3>
			<p class="mt-1 truncate font-mono text-xs text-ink-600">{path}</p>
			{#if sheet}
				<p class="mt-1 text-xs text-ink-500">
					{sheet.rows.length.toLocaleString()} rows · {sheet.headers.length} columns
					{#if nonAsciiTotal > 0}
						· <span class="font-semibold text-amber-700"
							>{nonAsciiTotal.toLocaleString()} non-ASCII cells</span
						>
					{/if}
				</p>
			{/if}
		</div>
		<div class="flex items-center gap-2">
			<div class="flex gap-1 rounded-lg bg-ink-50 p-1 ring-1 ring-ink-200">
				<button
					type="button"
					class={tabClass(view === 'rows')}
					aria-pressed={view === 'rows'}
					onclick={() => (view = 'rows')}>Rows</button
				>
				<button
					type="button"
					class={tabClass(view === 'columns')}
					aria-pressed={view === 'columns'}
					onclick={() => (view = 'columns')}>Columns</button
				>
			</div>
			<button
				type="button"
				class="rounded p-1.5 text-ink-400 hover:bg-ink-100 hover:text-ink-700"
				title="Close viewer"
				aria-label="Close workbook viewer"
				onclick={onclose}
			>
				<svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>
	</header>

	<div class="px-6 py-4">
		{#if loading}
			<p class="text-sm text-ink-500">Reading workbook…</p>
		{:else if error}
			<p class="text-sm text-rose-600">Could not read {path}: {error}</p>
		{:else if !sheet}
			<p class="text-sm text-ink-500">This workbook has no sheets.</p>
		{:else}
			{#if sheets.length > 1}
				<div class="mb-3 flex flex-wrap gap-1">
					{#each sheets as s, i (s.name)}
						<button
							type="button"
							class={tabClass(i === sheetIndex)}
							onclick={() => {
								sheetIndex = i;
								pageIndex = 0;
							}}>{s.name}</button
						>
					{/each}
				</div>
			{/if}

			{#if view === 'rows'}
				<div class="mb-3 flex flex-wrap items-center justify-between gap-3">
					<input
						type="search"
						value={query}
						oninput={(e) => setQuery(e.currentTarget.value)}
						placeholder="Filter rows (any column)"
						aria-label="Filter rows"
						class="w-full max-w-xs rounded-md border border-ink-300 px-3 py-1.5 text-sm focus:border-navy-500 focus:ring-navy-500"
					/>
					<div class="flex items-center gap-2 text-xs text-ink-600">
						<span class="font-mono">
							{filtered.length.toLocaleString()} match{filtered.length === 1 ? '' : 'es'}
						</span>
						<button
							type="button"
							class="rounded border border-ink-200 px-2 py-1 hover:bg-ink-50 disabled:opacity-40"
							disabled={pageIndex === 0}
							onclick={() => pageIndex--}>Prev</button
						>
						<span class="font-mono">{pageIndex + 1} / {pageCount}</span>
						<button
							type="button"
							class="rounded border border-ink-200 px-2 py-1 hover:bg-ink-50 disabled:opacity-40"
							disabled={pageIndex >= pageCount - 1}
							onclick={() => pageIndex++}>Next</button
						>
					</div>
				</div>
				<div class="max-h-[32rem] overflow-auto rounded-md border border-ink-200">
					<table class="min-w-full text-[11px]">
						<thead class="sticky top-0 z-10 bg-ink-50 shadow-[0_1px_0_var(--color-ink-200)]">
							<tr>
								<th class="px-2 py-2 text-right font-mono font-normal text-ink-400">#</th>
								{#each sheet.headers as header, c (c)}
									<th class="px-3 py-2 text-left font-semibold whitespace-nowrap text-ink-700">
										<span class="mr-1 font-mono font-normal text-ink-400">{columnLetter(c)}</span
										>{header}
									</th>
								{/each}
							</tr>
						</thead>
						<tbody class="divide-y divide-ink-100">
							{#each pageRows as row (row.number)}
								<tr class="hover:bg-navy-50/40">
									<td class="px-2 py-1.5 text-right font-mono text-ink-400">{row.number}</td>
									{#each row.cells as cell, c (c)}
										<td
											class={[
												'px-3 py-1.5 font-mono whitespace-nowrap',
												nonAscii(cell) ? 'bg-amber-50 text-amber-900' : 'text-ink-800'
											]}
											title={nonAscii(cell) ? 'Contains non-ASCII characters' : undefined}
											>{cell}</td
										>
									{/each}
								</tr>
							{:else}
								<tr>
									<td class="px-3 py-4 text-ink-500" colspan={sheet.headers.length + 1}>
										No rows match “{query}”.
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else}
				<div class="overflow-x-auto rounded-md border border-ink-200">
					<table class="min-w-full divide-y divide-ink-200 text-xs">
						<thead
							class="bg-ink-50 text-[11px] font-semibold tracking-wider text-ink-500 uppercase"
						>
							<tr>
								<th class="px-3 py-2 text-left">Col</th>
								<th class="px-3 py-2 text-left">Name</th>
								<th class="px-3 py-2 text-right">Filled</th>
								<th class="px-3 py-2 text-right">Distinct</th>
								<th class="px-3 py-2 text-right">Non-ASCII</th>
								<th class="px-3 py-2 text-left">Sample values</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-ink-100">
							{#each columns as col (col.letter)}
								<tr>
									<td class="px-3 py-2 font-mono text-ink-400">{col.letter}</td>
									<td class="px-3 py-2 font-semibold whitespace-nowrap text-ink-900">{col.name}</td>
									<td
										class={[
											'px-3 py-2 text-right font-mono',
											col.filled === 0 ? 'text-ink-400' : 'text-ink-800'
										]}
									>
										{col.filled.toLocaleString()} / {sheet.rows.length.toLocaleString()}
									</td>
									<td class="px-3 py-2 text-right font-mono text-ink-800"
										>{col.distinct.toLocaleString()}</td
									>
									<td
										class={[
											'px-3 py-2 text-right font-mono',
											col.nonAscii > 0 ? 'font-semibold text-amber-700' : 'text-ink-400'
										]}>{col.nonAscii.toLocaleString()}</td
									>
									<td class="max-w-md truncate px-3 py-2 font-mono text-ink-600">
										{col.samples.join(' · ')}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		{/if}
	</div>
</section>
