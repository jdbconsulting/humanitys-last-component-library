<script lang="ts">
	import { autoBuild } from '$lib/auto-build.svelte';
	import { collidingVendors, sharedRoots, withReordered } from '$lib/collisions';
	import { allFamilies, type FamilyDef } from '$lib/libraries';
	import { appState } from '$lib/state.svelte';
	import SectionHeader from '../SectionHeader.svelte';

	/**
	 * Only families whose footprint names actually collided in the last
	 * build are ranked here. Rows are vendor keys (the ids the house merge
	 * and `settings.house_footprints.priority` use); `familyIds` maps them
	 * to catalog families for display.
	 */
	const ALL_FAMILIES: Map<string, FamilyDef> = new Map(allFamilies().map((f) => [f.id, f]));

	const report = $derived(autoBuild.collisions);
	const priority = $derived(appState.config.settings.house_footprints.priority);
	const orderedKeys = $derived(report ? collidingVendors(report, priority) : []);
	const roots = $derived(report ? sharedRoots(report) : []);
	const stale = $derived(!autoBuild.isCurrent(appState.snapshotConfig()));

	function family(key: string): FamilyDef | undefined {
		return ALL_FAMILIES.get(report?.familyIds[key] ?? key);
	}

	function sharedCount(key: string): number {
		return roots.filter((r) => r.vendors.includes(key)).length;
	}

	/** Highest-ranked vendor for a root under the current order. */
	function winner(vendors: string[]): string | undefined {
		return orderedKeys.find((key) => vendors.includes(key));
	}

	function setOrder(list: string[]) {
		appState.config.settings.house_footprints.priority = withReordered(priority, list);
	}

	// ── Drag-and-drop state ──────────────────────────────────────────────────
	let draggingId = $state<string | null>(null);
	let dragOverId = $state<string | null>(null);
	/** Insert before or after the target, from the cursor's vertical position. */
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
		const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
		dropEdge = e.clientY < rect.top + rect.height / 2 ? 'before' : 'after';
	}

	function onDrop(e: DragEvent, targetId: string) {
		e.preventDefault();
		if (!draggingId || draggingId === targetId) return resetDrag();
		const list = orderedKeys.filter((key) => key !== draggingId);
		const insertAt = list.indexOf(targetId);
		if (insertAt === -1) return resetDrag();
		list.splice(dropEdge === 'before' ? insertAt : insertAt + 1, 0, draggingId);
		setOrder(list);
		resetDrag();
	}

	function resetDrag() {
		draggingId = null;
		dragOverId = null;
	}

	// ── Move-up / move-down buttons (keyboard / accessibility path) ──────────
	function move(id: string, by: -1 | 1) {
		const list = [...orderedKeys];
		const idx = list.indexOf(id);
		const to = idx + by;
		if (idx === -1 || to < 0 || to >= list.length) return;
		[list[idx], list[to]] = [list[to], list[idx]];
		setOrder(list);
	}
</script>

<SectionHeader
	title="Footprint priorities"
	description="When two or more families emit the same footprint name, the house library keeps the geometry from the family ranked highest here. Only families whose footprints collide in the current build are listed."
/>

{#snippet info(title: string, body: string)}
	<div class="mt-6 flex items-start gap-3 rounded-lg border border-navy-200 bg-navy-50 p-5">
		<svg class="mt-0.5 h-5 w-5 shrink-0 text-navy-600" viewBox="0 0 20 20" fill="currentColor">
			<path
				fill-rule="evenodd"
				d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z"
				clip-rule="evenodd"
			/>
		</svg>
		<div>
			<p class="text-sm font-semibold text-navy-900">{title}</p>
			<p class="mt-1 text-sm text-navy-800">{body}</p>
		</div>
	</div>
{/snippet}

{#if report && stale}
	<p class="mt-4 inline-flex items-center gap-1.5 text-xs text-amber-700">
		<span class="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500"></span>
		Showing collisions from the previous build while the background build catches up.
	</p>
{/if}

{#if appState.enabledFamilyIds().length === 0}
	{@render info(
		'No families enabled',
		'Enable at least one family on the Libraries tab. Priorities only matter once two families emit the same footprint name.'
	)}
{:else if !report}
	{@render info(
		'Checking footprint names…',
		appState.ui.auto_build
			? 'The background build is generating the library. Families with colliding footprint names will be listed here when it finishes.'
			: 'Automatic rebuilds are off. Build on the Generate tab to find footprint names that collide.'
	)}
{:else if orderedKeys.length === 0}
	{@render info(
		'No footprint names collide',
		'Every footprint in the current build comes from exactly one family, so the priority order has no effect. Names can only overlap when two or more families use generic IPC-7351B footprint names (Libraries tab → family card → Footprint names) for the same body size and height.'
	)}
{:else}
	<div class="mt-5 overflow-hidden rounded-lg border border-ink-200 bg-white shadow-sm">
		<div
			class="grid grid-cols-[2rem_2rem_1fr_auto] items-center gap-4 border-b border-ink-200 bg-ink-50 px-4 py-2.5 text-[11px] font-semibold tracking-[0.15em] text-ink-500 uppercase"
		>
			<span class="text-center">#</span>
			<span></span>
			<span>Family</span>
			<span class="pr-1">Move</span>
		</div>

		<ul class="divide-y divide-ink-100" role="list" ondragover={(e) => e.preventDefault()}>
			{#each orderedKeys as id, i (id)}
				{@const fam = family(id)}
				{@const isDragging = draggingId === id}
				{@const isTarget = dragOverId === id && draggingId !== id}
				<li
					draggable="true"
					ondragstart={(e) => onDragStart(e, id)}
					ondragover={(e) => onDragOver(e, id)}
					ondrop={(e) => onDrop(e, id)}
					ondragend={resetDrag}
					class={[
						'grid grid-cols-[2rem_2rem_1fr_auto] items-center gap-4 px-4 py-3 transition-colors',
						isDragging
							? 'bg-navy-50 opacity-50'
							: 'cursor-grab hover:bg-ink-50 active:cursor-grabbing',
						isTarget && dropEdge === 'before' ? 'border-t-2 border-t-accent-500' : '',
						isTarget && dropEdge === 'after' ? 'border-b-2 border-b-accent-500' : ''
					]}
					role="listitem"
				>
					<span
						class={[
							'flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold tabular-nums',
							i === 0 ? 'bg-accent-500 text-navy-950' : 'bg-ink-100 text-ink-600'
						]}
					>
						{i + 1}
					</span>
					<span class="flex items-center justify-center text-ink-400">
						<svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
							<path
								d="M7 3a1 1 0 000 2h6a1 1 0 100-2H7zM4 7a1 1 0 011-1h10a1 1 0 110 2H5a1 1 0 01-1-1zm1 4a1 1 0 100 2h10a1 1 0 100-2H5zm-1 5a1 1 0 011-1h10a1 1 0 110 2H5a1 1 0 01-1-1z"
							/>
						</svg>
					</span>
					<div class="min-w-0">
						<div class="flex items-center gap-2">
							<span class="truncate text-sm font-semibold text-ink-900">{fam?.name ?? id}</span>
							<span
								class="shrink-0 rounded bg-ink-100 px-1.5 py-0.5 font-mono text-[10px] font-medium text-ink-600"
							>
								{fam?.id ?? id}
							</span>
						</div>
						<p class="mt-0.5 text-xs text-ink-500">
							Shares {sharedCount(id)} footprint{sharedCount(id) === 1 ? '' : 's'} with other families
						</p>
					</div>
					<div class="flex items-center gap-1">
						<button
							type="button"
							onclick={() => move(id, -1)}
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
							onclick={() => move(id, 1)}
							disabled={i === orderedKeys.length - 1}
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

	<section class="mt-6 overflow-hidden rounded-lg border border-ink-200 bg-white shadow-sm">
		<header class="border-b border-ink-200 px-4 py-3">
			<h3 class="text-sm font-semibold text-ink-900">Shared footprints</h3>
			<p class="mt-0.5 text-xs text-ink-500">
				{roots.length} footprint{roots.length === 1 ? '' : 's'}, each with its L/N/M density
				variants. The winner is the highest-ranked family; reordering takes effect in the next
				build.
			</p>
		</header>
		<div class="max-h-[28rem] overflow-auto">
			<table class="min-w-full divide-y divide-ink-200 text-xs">
				<thead
					class="sticky top-0 bg-ink-50 text-[11px] font-semibold tracking-wider text-ink-500 uppercase"
				>
					<tr>
						<th class="px-4 py-2 text-left">Footprint</th>
						<th class="px-4 py-2 text-left">Geometry</th>
						<th class="px-4 py-2 text-left">Families (winner first)</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-ink-100">
					{#each roots as r (r.root)}
						{@const top = winner(r.vendors)}
						<tr>
							<td class="px-4 py-2 font-mono whitespace-nowrap text-ink-900">
								{r.root}<span class="text-ink-400">{r.densities.join('/')}</span>
							</td>
							<td class="px-4 py-2 whitespace-nowrap">
								<span
									class={[
										'rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset',
										r.sameGeometry
											? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
											: 'bg-amber-50 text-amber-800 ring-amber-200'
									]}
								>
									{r.sameGeometry ? 'Identical' : 'Differs'}
								</span>
							</td>
							<td class="px-4 py-2 text-ink-700">
								{#each orderedKeys.filter((key) => r.vendors.includes(key)) as key, i (key)}
									<span class={key === top ? 'font-semibold text-ink-900' : 'text-ink-500'}
										>{family(key)?.name ?? key}</span
									>{i < r.vendors.length - 1 ? ', ' : ''}
								{/each}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</section>

	<p class="mt-4 text-xs text-ink-500">
		“Differs” means the families disagree on body, terminal, land pattern or 3D model, so the order
		changes the footprint you get. Choose vendor-specific footprint names on a family's card to take
		it out of a collision entirely.
	</p>
{/if}
