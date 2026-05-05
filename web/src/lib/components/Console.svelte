<script lang="ts">
	import { consoleLog, type ConsoleEntry, type ConsoleLevel } from '$lib/console.svelte';
	import { tick } from 'svelte';

	let { collapsed = $bindable(false) }: { collapsed?: boolean } = $props();

	let scrollEl: HTMLDivElement | undefined = $state();
	let autoscroll = $state(true);

	const levelClass: Record<ConsoleLevel, string> = {
		info: 'text-sky-400',
		warn: 'text-amber-400',
		error: 'text-rose-400',
		stdout: 'text-slate-100',
		stderr: 'text-rose-300',
		system: 'text-emerald-400'
	};

	const levelLabel: Record<ConsoleLevel, string> = {
		info: 'INFO',
		warn: 'WARN',
		stdout: 'OUT ',
		stderr: 'ERR ',
		error: 'ERR ',
		system: 'SYS '
	};

	function fmtTime(t: number): string {
		const d = new Date(t);
		return d.toLocaleTimeString('en-GB', { hour12: false });
	}

	$effect.pre(() => {
		// Track entry count so the effect re-runs whenever a new line lands.
		void consoleLog.entries.length;
		if (!autoscroll || !scrollEl) return;
		tick().then(() => {
			if (scrollEl) scrollEl.scrollTop = scrollEl.scrollHeight;
		});
	});

	function entryKey(e: ConsoleEntry): number {
		return e.id;
	}
</script>

<aside
	class={[
		'flex flex-col border-t border-navy-800 bg-navy-900 font-mono text-xs text-ink-100 transition-all',
		collapsed ? 'h-10' : 'h-72'
	]}
>
	<div
		class="flex h-10 shrink-0 items-center justify-between border-b border-navy-800 bg-navy-950 px-4"
	>
		<button
			type="button"
			class="flex items-center gap-2 text-ink-200 hover:text-white"
			onclick={() => (collapsed = !collapsed)}
			aria-label={collapsed ? 'Expand console' : 'Collapse console'}
		>
			<svg
				class={['h-3.5 w-3.5 transition-transform', collapsed ? '-rotate-90' : 'rotate-0']}
				viewBox="0 0 12 12"
				fill="currentColor"
			>
				<path d="M3 4.5l3 3 3-3z" />
			</svg>
			<span class="text-[11px] font-semibold tracking-wider uppercase">Python console</span>
			<span class="text-[11px] text-ink-500">({consoleLog.entries.length})</span>
		</button>

		<div class="flex items-center gap-3">
			<label class="flex items-center gap-1.5 text-[11px] text-ink-300">
				<input
					type="checkbox"
					bind:checked={autoscroll}
					class="h-3 w-3 rounded border-navy-700 bg-navy-800 text-accent-500 focus:ring-accent-500"
				/>
				autoscroll
			</label>
			<button
				type="button"
				class="rounded border border-navy-700 bg-navy-800 px-2 py-0.5 text-[11px] text-ink-200 hover:bg-navy-700"
				onclick={() => consoleLog.clear()}
			>
				Clear
			</button>
		</div>
	</div>

	{#if !collapsed}
		<div bind:this={scrollEl} class="flex-1 overflow-auto px-4 py-2 leading-snug">
			{#if consoleLog.entries.length === 0}
				<div class="text-ink-500">
					<span class="text-emerald-400">$</span> Console idle. Load Pyodide on the
					<em class="text-ink-300 not-italic">Generate</em> tab to begin.
				</div>
			{:else}
				{#each consoleLog.entries as entry (entryKey(entry))}
					<div class="flex gap-2 break-words whitespace-pre-wrap">
						<span class="shrink-0 text-ink-600">{fmtTime(entry.timestamp)}</span>
						<span class={['shrink-0 font-semibold', levelClass[entry.level]]}>
							{levelLabel[entry.level]}
						</span>
						<span
							class={entry.level === 'stderr' || entry.level === 'error' ? 'text-rose-200' : ''}
						>
							{entry.text}
						</span>
					</div>
				{/each}
			{/if}
		</div>
	{/if}
</aside>
