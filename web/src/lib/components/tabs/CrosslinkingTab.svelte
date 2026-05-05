<script lang="ts">
	import { appState } from '$lib/state.svelte';
	import SectionHeader from '../SectionHeader.svelte';
</script>

<SectionHeader
	title="MPN / MFG cross-link substitutes"
	description="Define alternate-part substitutions used by downstream BOM tools. Each row maps a primary MPN/MFG to one substitute. Build-side cross-linking ships in a future release; the configurator captures the data now so it stays alongside the rest of the run."
/>

<div class="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
	<strong>Note:</strong> the project root does not yet implement the cross-link generator — these rows
	are persisted with the rest of your configuration so they're ready when the build chain picks them up.
	Export them now via the Generate tab to bootstrap your own tooling in the meantime.
</div>

<div class="mt-6 overflow-hidden rounded-lg border border-ink-200 bg-white">
	<table class="min-w-full divide-y divide-ink-200">
		<thead class="bg-ink-50">
			<tr class="text-left text-[11px] font-semibold tracking-wider text-ink-500 uppercase">
				<th class="px-4 py-2">Primary MPN</th>
				<th class="px-4 py-2">Primary MFG</th>
				<th class="px-4 py-2">Substitute MPN</th>
				<th class="px-4 py-2">Substitute MFG</th>
				<th class="px-4 py-2">Notes</th>
				<th class="px-2 py-2"></th>
			</tr>
		</thead>
		<tbody class="divide-y divide-ink-100">
			{#each appState.crosslinks as row (row.id)}
				<tr>
					<td class="px-4 py-2">
						<input
							class="w-full rounded-md border-ink-200 font-mono text-xs"
							placeholder="ERJ-3EKF1002V"
							bind:value={row.primary_mpn}
						/>
					</td>
					<td class="px-4 py-2">
						<input
							class="w-full rounded-md border-ink-200 text-xs"
							placeholder="Panasonic"
							bind:value={row.primary_mfg}
						/>
					</td>
					<td class="px-4 py-2">
						<input
							class="w-full rounded-md border-ink-200 font-mono text-xs"
							placeholder="RC0603FR-0710KL"
							bind:value={row.substitute_mpn}
						/>
					</td>
					<td class="px-4 py-2">
						<input
							class="w-full rounded-md border-ink-200 text-xs"
							placeholder="Yageo"
							bind:value={row.substitute_mfg}
						/>
					</td>
					<td class="px-4 py-2">
						<input
							class="w-full rounded-md border-ink-200 text-xs"
							placeholder="Drop-in equivalent"
							bind:value={row.notes}
						/>
					</td>
					<td class="px-2 py-2 text-right">
						<button
							type="button"
							class="rounded p-1.5 text-ink-400 hover:bg-rose-50 hover:text-rose-600"
							onclick={() => appState.removeCrosslink(row.id)}
							aria-label="Remove row"
						>
							<svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"
								><path
									fill-rule="evenodd"
									d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 100 2h12a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM5 8a1 1 0 011 1v7a1 1 0 11-2 0V9a1 1 0 011-1zm5 0a1 1 0 011 1v7a1 1 0 11-2 0V9a1 1 0 011-1zm5 0a1 1 0 011 1v7a1 1 0 11-2 0V9a1 1 0 011-1z"
									clip-rule="evenodd"
								/></svg
							>
						</button>
					</td>
				</tr>
			{/each}
			{#if appState.crosslinks.length === 0}
				<tr>
					<td colspan="6" class="px-4 py-12 text-center text-sm text-ink-500">
						No cross-link substitutes defined yet.
					</td>
				</tr>
			{/if}
		</tbody>
	</table>
	<div class="border-t border-ink-200 bg-ink-50 px-4 py-3">
		<button
			type="button"
			class="inline-flex items-center gap-1.5 rounded-md border border-ink-300 bg-white px-3 py-1.5 text-sm font-medium text-ink-700 shadow-sm hover:bg-ink-50"
			onclick={() => appState.addCrosslink()}
		>
			<svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"
				><path
					fill-rule="evenodd"
					d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z"
					clip-rule="evenodd"
				/></svg
			>
			Add row
		</button>
	</div>
</div>
