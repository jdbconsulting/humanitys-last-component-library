<script lang="ts">
	import { appState } from '$lib/state.svelte';
	import { allFamilies, type FamilyDef } from '$lib/libraries';
	import SectionHeader from '../SectionHeader.svelte';

	/**
	 * Derive the ordered priority list from `appState.project.priority`,
	 * merging in any enabled families that aren't yet in the list.
	 *
	 * We never mutate this derived array directly — we only use it for rendering
	 * and write back to `appState.project.priority` on drop.
	 */
	const ALL_FAMILIES: Map<string, FamilyDef> = new Map(allFamilies().map((f) => [f.id, f]));

	function buildOrderedList(): string[] {
		const enabled = new Set(appState.enabledFamilyIds());
		// Start with the saved priority order, keeping only what's enabled.
		const ordered = appState.project.priority.filter((id) => enabled.has(id));
		// Append any enabled families that haven't been ranked yet (newly enabled).
		for (const id of enabled) {
			if (!ordered.includes(id)) ordered.push(id);
		}
		return ordered;
	}

	const orderedIds = $derived(buildOrderedList());

	// ── Drag-and-drop state ──────────────────────────────────────────────────
	let draggingId = $state<string | null>(null);
	let dragOverId = $state<string | null>(null);
	/**
	 * Whether the dragged item is being inserted BEFORE the target (`'before'`)
	 * or AFTER (`'after'`), determined by the vertical cursor position.
	 */
	let dropEdge = $state<'before' | 'after'>('before');

	function onDragStart(e: DragEvent, id: string) {
		draggingId = id;
		if (e.dataTransfer) {
			e.dataTransfer.effectAllowed = 'move';
			e.dataTransfer.setData('text/plain', id);
		}
	}

	function onDragOver(e: DragEvent, id: string) {
		e.preventDefault();
		if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
		dragOverId = id;
		// Determine edge from cursor position relative to the row mid-point.
		const target = e.currentTarget as HTMLElement;
		const rect = target.getBoundingClientRect();
		dropEdge = e.clientY < rect.top + rect.height / 2 ? 'before' : 'after';
	}

	function onDrop(e: DragEvent, targetId: string) {
		e.preventDefault();
		if (!draggingId || draggingId === targetId) return resetDrag();

		const list = [...orderedIds];
		const fromIdx = list.indexOf(draggingId);
		const toIdx = list.indexOf(targetId);
		if (fromIdx === -1 || toIdx === -1) return resetDrag();

		list.splice(fromIdx, 1);
		const insertAt = list.indexOf(targetId);
		list.splice(dropEdge === 'before' ? insertAt : insertAt + 1, 0, draggingId);

		appState.project.priority = list;
		resetDrag();
	}

	function onDragEnd() {
		resetDrag();
	}

	function resetDrag() {
		draggingId = null;
		dragOverId = null;
	}

	// ── Move-up / move-down buttons (keyboard / accessibility path) ──────────
	function moveUp(id: string) {
		const list = [...orderedIds];
		const idx = list.indexOf(id);
		if (idx <= 0) return;
		[list[idx - 1], list[idx]] = [list[idx], list[idx - 1]];
		appState.project.priority = list;
	}

	function moveDown(id: string) {
		const list = [...orderedIds];
		const idx = list.indexOf(id);
		if (idx === -1 || idx >= list.length - 1) return;
		[list[idx], list[idx + 1]] = [list[idx + 1], list[idx]];
		appState.project.priority = list;
	}
</script>

<SectionHeader
	title="Footprint priorities"
	description="When two enabled vendor families emit the same IPC-7351B footprint identifier (e.g. RESC1005X35N), the house library uses the family highest in this list as the authoritative source for pad geometry and mask rules. Drag rows to reorder, or use the arrow buttons."
/>

{#if orderedIds.length === 0}
	<div class="mt-8 rounded-lg border border-dashed border-ink-300 bg-ink-50 p-10 text-center">
		<svg
			class="mx-auto h-10 w-10 text-ink-300"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="1.5"
			stroke-linecap="round"
			stroke-linejoin="round"
		>
			<path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2" />
			<rect x="9" y="3" width="6" height="4" rx="1" />
		</svg>
		<p class="mt-3 text-sm font-medium text-ink-600">No vendor families enabled yet.</p>
		<p class="mt-1 text-xs text-ink-500">
			Go back to the Libraries tab and enable at least one family.
		</p>
	</div>
{:else}
	<div class="mt-5 overflow-hidden rounded-lg border border-ink-200 bg-white shadow-sm">
		<!-- Header row -->
		<div
			class="grid grid-cols-[2rem_2rem_1fr_auto] items-center gap-4 border-b border-ink-200 bg-ink-50 px-4 py-2.5 text-[11px] font-semibold tracking-[0.15em] text-ink-500 uppercase"
		>
			<span class="text-center">#</span>
			<span></span>
			<span>Family</span>
			<span class="pr-1">Move</span>
		</div>

		<ul
			class="divide-y divide-ink-100"
			role="list"
			ondragover={(e) => e.preventDefault()}
		>
			{#each orderedIds as id, i (id)}
				{@const fam = ALL_FAMILIES.get(id)}
				{@const isDragging = draggingId === id}
				{@const isTarget = dragOverId === id && draggingId !== id}

				<li
					draggable="true"
					ondragstart={(e) => onDragStart(e, id)}
					ondragover={(e) => onDragOver(e, id)}
					ondrop={(e) => onDrop(e, id)}
					ondragend={onDragEnd}
					class={[
						'grid grid-cols-[2rem_2rem_1fr_auto] items-center gap-4 px-4 py-3 transition-colors',
						isDragging
							? 'bg-navy-50 opacity-50'
							: 'cursor-grab hover:bg-ink-50 active:cursor-grabbing',
						isTarget && dropEdge === 'before'
							? 'border-t-2 border-t-accent-500'
							: '',
						isTarget && dropEdge === 'after'
							? 'border-b-2 border-b-accent-500'
							: ''
					]}
					role="listitem"
				>
					<!-- Rank badge -->
					<span
						class={[
							'flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold tabular-nums',
							i === 0
								? 'bg-accent-500 text-navy-950'
								: i === 1
									? 'bg-navy-900 text-white'
									: i === 2
										? 'bg-navy-700 text-white'
										: 'bg-ink-100 text-ink-600'
						]}
					>
						{i + 1}
					</span>

					<!-- Drag handle -->
					<span class="flex items-center justify-center text-ink-400">
						<svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
							<path d="M7 3a1 1 0 000 2h6a1 1 0 100-2H7zM4 7a1 1 0 011-1h10a1 1 0 110 2H5a1 1 0 01-1-1zm1 4a1 1 0 100 2h10a1 1 0 100-2H5zm-1 5a1 1 0 011-1h10a1 1 0 110 2H5a1 1 0 01-1-1z" />
						</svg>
					</span>

					<!-- Family details -->
					<div class="min-w-0">
						<div class="flex items-center gap-2">
							<span class="truncate text-sm font-semibold text-ink-900">
								{fam?.name ?? id}
							</span>
							<span
								class="shrink-0 rounded bg-ink-100 px-1.5 py-0.5 font-mono text-[10px] font-medium text-ink-600"
							>
								{id}
							</span>
						</div>
						{#if fam}
							<p class="mt-0.5 truncate text-xs text-ink-500">
								{fam.manufacturer} · {fam.summary}
							</p>
						{/if}
					</div>

					<!-- Move up / down buttons -->
					<div class="flex items-center gap-1">
						<button
							type="button"
							onclick={() => moveUp(id)}
							disabled={i === 0}
							class="rounded p-1 text-ink-400 hover:bg-ink-100 hover:text-ink-700 disabled:cursor-not-allowed disabled:opacity-25"
							aria-label="Move {fam?.name ?? id} up"
						>
							<svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
								<path
									fill-rule="evenodd"
									d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>
						<button
							type="button"
							onclick={() => moveDown(id)}
							disabled={i === orderedIds.length - 1}
							class="rounded p-1 text-ink-400 hover:bg-ink-100 hover:text-ink-700 disabled:cursor-not-allowed disabled:opacity-25"
							aria-label="Move {fam?.name ?? id} down"
						>
							<svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
								<path
									fill-rule="evenodd"
									d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>
					</div>
				</li>
			{/each}
		</ul>
	</div>

	<div class="mt-4 flex items-start gap-2 text-xs text-ink-500">
		<svg
			class="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-400"
			viewBox="0 0 20 20"
			fill="currentColor"
		>
			<path
				fill-rule="evenodd"
				d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z"
				clip-rule="evenodd"
			/>
		</svg>
		<span>
			Enabling or disabling a family in the Libraries tab will automatically move it to the
			bottom of this list if not already ranked. The priority list only affects families that
			share an overlapping IPC footprint identifier — independent families are unaffected.
		</span>
	</div>
{/if}
