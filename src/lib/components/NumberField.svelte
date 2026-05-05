<script lang="ts">
	interface Props {
		label: string;
		value: number;
		min?: number;
		max?: number;
		step?: number;
		unit?: string;
		help?: string;
		disabled?: boolean;
		onchange?: (v: number) => void;
	}
	let {
		label,
		value = $bindable(),
		min,
		max,
		step,
		unit,
		help,
		disabled = false,
		onchange
	}: Props = $props();
</script>

<label class="block">
	<span class="text-sm font-medium text-ink-800">{label}</span>
	<div class="mt-1 flex items-center gap-2">
		<input
			type="number"
			class={[
				'block w-full max-w-[10rem] rounded-md border-ink-300 text-sm shadow-sm focus:border-navy-500 focus:ring-navy-500',
				disabled && 'bg-ink-50 text-ink-400'
			]}
			bind:value
			{min}
			{max}
			{step}
			{disabled}
			onchange={() => onchange?.(value)}
		/>
		{#if unit}
			<span class="text-xs text-ink-500">{unit}</span>
		{/if}
	</div>
	{#if help}
		<p class="mt-1 text-xs text-ink-500">{help}</p>
	{/if}
</label>
