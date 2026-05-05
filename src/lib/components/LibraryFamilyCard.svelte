<script lang="ts">
	import type { FamilyDef } from '$lib/libraries';
	import { appState } from '$lib/state.svelte';
	import type { FamilyConfig } from '$lib/schema';
	import Toggle from './Toggle.svelte';

	let { family }: { family: FamilyDef } = $props();

	const fam: FamilyConfig = $derived(appState.config.families[family.id]);
	let expanded = $state(false);

	function toggleMultiselectChoice(optId: string, choiceId: string) {
		const cur = fam.options[optId];
		if (!Array.isArray(cur)) return;
		const idx = cur.indexOf(choiceId);
		if (idx >= 0) cur.splice(idx, 1);
		else cur.push(choiceId);
	}

	function isSelected(optId: string, choiceId: string): boolean {
		const cur = fam.options[optId];
		return Array.isArray(cur) && cur.includes(choiceId);
	}

	function isOverridden(optId: string): boolean {
		return fam.overrides?.[optId] === true;
	}

	function setOverride(optId: string, override: boolean) {
		fam.overrides[optId] = override;
	}
</script>

<div
	class={[
		'rounded-lg border bg-white shadow-sm transition',
		fam.enabled ? 'border-navy-300 ring-1 ring-navy-200' : 'border-ink-200'
	]}
>
	<div class="flex items-start gap-3 p-4">
		<Toggle bind:checked={fam.enabled} label="" help="" />
		<button
			type="button"
			class="flex flex-1 items-start justify-between text-left"
			onclick={() => (expanded = !expanded)}
		>
			<div>
				<div class="flex items-center gap-2">
					<span class="text-sm font-semibold text-ink-900">{family.name}</span>
					<span
						class="rounded bg-ink-100 px-1.5 py-0.5 font-mono text-[10px] font-medium text-ink-600"
					>
						{family.id}
					</span>
				</div>
				<p class="mt-0.5 text-xs text-ink-600">{family.summary}</p>
				<p class="mt-1 text-[11px] tracking-wider text-ink-500 uppercase">{family.manufacturer}</p>
			</div>
			<svg
				class={[
					'h-4 w-4 shrink-0 text-ink-400 transition-transform',
					expanded ? 'rotate-180' : 'rotate-0'
				]}
				viewBox="0 0 12 12"
				fill="currentColor"
			>
				<path d="M3 4.5l3 3 3-3z" />
			</svg>
		</button>
	</div>

	{#if expanded}
		<div class="space-y-4 border-t border-ink-200 bg-ink-50 px-4 py-4">
			{#if family.options.length === 0}
				<p class="text-xs text-ink-500 italic">No family-specific options.</p>
			{/if}
			{#each family.options as opt (opt.id)}
				<div>
					<div class="flex items-center justify-between gap-3">
						<label class="text-sm font-medium text-ink-800" for={`${family.id}-${opt.id}`}>
							{opt.label}
						</label>
						{#if opt.overridesGlobal}
							<div
								class="inline-flex overflow-hidden rounded-md border border-ink-200 bg-white text-[11px] font-medium"
							>
								<button
									type="button"
									class={[
										'px-2 py-0.5',
										!isOverridden(opt.id)
											? 'bg-navy-900 text-white'
											: 'text-ink-600 hover:bg-ink-100'
									]}
									onclick={() => setOverride(opt.id, false)}
								>
									Use global
								</button>
								<button
									type="button"
									class={[
										'border-l border-ink-200 px-2 py-0.5',
										isOverridden(opt.id)
											? 'bg-navy-900 text-white'
											: 'text-ink-600 hover:bg-ink-100'
									]}
									onclick={() => setOverride(opt.id, true)}
								>
									Override
								</button>
							</div>
						{/if}
					</div>

					{#if opt.help}
						<p class="mt-0.5 text-xs text-ink-500">{opt.help}</p>
					{/if}

					{#if opt.control.kind === 'toggle'}
						<div class="mt-2">
							<Toggle checked={fam.options[opt.id] === true} label="Enabled" size="sm" />
						</div>
					{:else if opt.control.kind === 'select'}
						<select
							id={`${family.id}-${opt.id}`}
							class="mt-2 block w-full max-w-sm rounded-md border-ink-300 text-sm shadow-sm focus:border-navy-500 focus:ring-navy-500 disabled:bg-ink-100 disabled:text-ink-400"
							value={fam.options[opt.id] as string}
							onchange={(e) => (fam.options[opt.id] = (e.target as HTMLSelectElement).value)}
							disabled={opt.overridesGlobal && !isOverridden(opt.id)}
						>
							{#each opt.control.choices as choice (choice.id)}
								<option value={choice.id}>{choice.label}</option>
							{/each}
						</select>
					{:else if opt.control.kind === 'multiselect'}
						{@const globalLocked = opt.overridesGlobal && !isOverridden(opt.id)}
						<div class="mt-2 flex flex-wrap gap-2">
							{#each opt.control.choices as choice (choice.id)}
								<button
									type="button"
									disabled={globalLocked}
									class={[
										'rounded-full border px-3 py-1 text-xs font-medium transition',
										globalLocked
											? 'cursor-not-allowed border-ink-100 bg-ink-50 text-ink-300'
											: isSelected(opt.id, choice.id)
												? 'border-navy-300 bg-navy-50 text-navy-800'
												: 'border-ink-200 bg-white text-ink-600 hover:border-ink-300'
									]}
									onclick={() => !globalLocked && toggleMultiselectChoice(opt.id, choice.id)}
								>
									{choice.label}
								</button>
							{/each}
						</div>
					{:else if opt.control.kind === 'number'}
						<div class="mt-2 flex items-center gap-2">
							<input
								id={`${family.id}-${opt.id}`}
								type="number"
								class="block w-32 rounded-md border-ink-300 text-sm shadow-sm focus:border-navy-500 focus:ring-navy-500 disabled:bg-ink-100 disabled:text-ink-400"
								value={fam.options[opt.id] as number}
								oninput={(e) =>
									(fam.options[opt.id] = Number((e.target as HTMLInputElement).value))}
								min={opt.control.min}
								max={opt.control.max}
								step={opt.control.step}
								disabled={opt.overridesGlobal && !isOverridden(opt.id)}
							/>
							{#if opt.control.unit}
								<span class="text-xs text-ink-500">{opt.control.unit}</span>
							{/if}
						</div>
					{:else if opt.control.kind === 'text'}
						<input
							id={`${family.id}-${opt.id}`}
							type="text"
							class="mt-2 block w-full max-w-md rounded-md border-ink-300 text-sm shadow-sm focus:border-navy-500 focus:ring-navy-500 disabled:bg-ink-100 disabled:text-ink-400"
							value={fam.options[opt.id] as string}
							placeholder={opt.control.placeholder}
							oninput={(e) => (fam.options[opt.id] = (e.target as HTMLInputElement).value)}
							disabled={opt.overridesGlobal && !isOverridden(opt.id)}
						/>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>
