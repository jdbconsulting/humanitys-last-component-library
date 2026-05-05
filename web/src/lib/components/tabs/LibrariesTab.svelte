<script lang="ts">
	import { LIBRARY_CATALOG } from '$lib/libraries';
	import { appState } from '$lib/state.svelte';
	import LibraryFamilyCard from '../LibraryFamilyCard.svelte';
	import NumberField from '../NumberField.svelte';
	import SectionHeader from '../SectionHeader.svelte';

	let enabledCount = $derived(appState.enabledFamilyIds().length);
	let totalFamilies = $derived(
		LIBRARY_CATALOG.reduce(
			(acc, k) => acc + k.subtypes.reduce((a, s) => a + s.families.length, 0),
			0
		)
	);

	let activeKindId = $state(LIBRARY_CATALOG[0]?.id ?? 'resistor');
	let activeKind = $derived(
		LIBRARY_CATALOG.find((k) => k.id === activeKindId) ?? LIBRARY_CATALOG[0]
	);
</script>

<SectionHeader
	title="Component family libraries"
	description="Pick the vendor families to include. Each family can override the project-wide defaults from the next tab; leave any option on “Use global” to inherit from the project settings."
/>

<div class="mt-6 grid gap-6 lg:grid-cols-[18rem_1fr]">
	<aside class="space-y-4">
		<div class="rounded-lg border border-ink-200 bg-white p-4">
			<div class="flex items-center justify-between">
				<span class="text-sm font-medium text-ink-700">Selection</span>
				<span class="font-mono text-xs text-ink-500">{enabledCount} / {totalFamilies}</span>
			</div>
			<div class="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-ink-100">
				<div
					class="h-full bg-gradient-to-r from-navy-500 to-emerald-500 transition-all"
					style:width={`${totalFamilies === 0 ? 0 : (enabledCount / totalFamilies) * 100}%`}
				></div>
			</div>
			<p class="mt-3 text-xs text-ink-500">
				At least one family must be enabled before generation can proceed.
			</p>
		</div>

		<nav class="rounded-lg border border-ink-200 bg-white p-2">
			{#each LIBRARY_CATALOG as kind (kind.id)}
				{@const ids = kind.subtypes.flatMap((s) => s.families.map((f) => f.id))}
				{@const count = ids.filter((id) => appState.families[id]?.enabled).length}
				<button
					type="button"
					onclick={() => (activeKindId = kind.id)}
					class={[
						'flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm font-medium transition',
						activeKindId === kind.id ? 'bg-navy-900 text-white' : 'text-ink-700 hover:bg-ink-100'
					]}
				>
					<span>{kind.label}</span>
					<span
						class={[
							'rounded px-1.5 py-0.5 font-mono text-[10px]',
							activeKindId === kind.id ? 'bg-ink-700 text-ink-100' : 'bg-ink-100 text-ink-600'
						]}
					>
						{count}/{ids.length}
					</span>
				</button>
			{/each}
		</nav>

		<div class="rounded-lg border border-amber-200 bg-amber-50 p-4">
			<h3 class="text-xs font-semibold tracking-wider text-amber-800 uppercase">
				Globals (preview)
			</h3>
			<p class="mt-1 text-xs text-amber-700">
				These hold the values per-family options inherit when set to “Use global”.
			</p>
			<div class="mt-3 space-y-2">
				<NumberField
					label="Pad corner radius"
					bind:value={appState.project.hlcl.pad_corner_radius_percent}
					min={0}
					max={50}
					step={1}
					unit="%"
				/>
			</div>
		</div>
	</aside>

	<div class="space-y-8">
		{#each activeKind.subtypes as sub (sub.id)}
			<section>
				<div class="flex items-baseline justify-between">
					<h3 class="text-base font-semibold text-ink-800">{sub.label}</h3>
					<span class="text-xs text-ink-500">{sub.families.length} families</span>
				</div>
				<div class="mt-3 grid gap-3 md:grid-cols-2">
					{#each sub.families as fam (fam.id)}
						<LibraryFamilyCard family={fam} />
					{/each}
					{#if sub.families.length === 0}
						<div
							class="col-span-full rounded-md border border-dashed border-ink-300 bg-ink-50 p-6 text-center text-sm text-ink-500"
						>
							No vendor families in this subtype yet — contributions welcome.
						</div>
					{/if}
				</div>
			</section>
		{/each}
	</div>
</div>
