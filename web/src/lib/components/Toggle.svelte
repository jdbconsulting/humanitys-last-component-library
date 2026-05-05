<script lang="ts">
	interface Props {
		checked: boolean;
		label: string;
		help?: string;
		size?: 'sm' | 'md';
	}
	let { checked = $bindable(), label, help, size = 'md' }: Props = $props();

	const trackClass = $derived(size === 'sm' ? 'h-4 w-7' : 'h-5 w-9');
	const thumbClass = $derived(size === 'sm' ? 'h-3 w-3' : 'h-4 w-4');
	const thumbOn = $derived(size === 'sm' ? 'translate-x-3' : 'translate-x-4');
</script>

<label class="flex cursor-pointer items-start gap-3">
	<button
		type="button"
		role="switch"
		aria-checked={checked}
		aria-label={label || 'Toggle'}
		onclick={() => (checked = !checked)}
		class={[
			'relative shrink-0 rounded-full border border-transparent transition-colors',
			trackClass,
			checked ? 'bg-navy-600' : 'bg-ink-300'
		]}
	>
		<span
			class={[
				'absolute top-0.5 left-0.5 inline-block rounded-full bg-white shadow transition-transform',
				thumbClass,
				checked ? thumbOn : 'translate-x-0'
			]}
		></span>
	</button>
	<div class="-mt-0.5 leading-tight">
		<div class={[size === 'sm' ? 'text-sm' : 'text-sm font-medium', 'text-ink-800']}>{label}</div>
		{#if help}<p class="mt-0.5 text-xs text-ink-500">{help}</p>{/if}
	</div>
</label>
