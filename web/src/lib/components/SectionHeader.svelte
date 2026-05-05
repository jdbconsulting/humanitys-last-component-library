<script lang="ts">
	let { title, description }: { title: string; description?: string } = $props();
</script>

<div class="border-b border-ink-200 pb-4">
	<h2 class="text-xl font-semibold tracking-tight text-ink-900">{title}</h2>
	{#if description}
		<p class="mt-1 text-sm text-ink-600">{description}</p>
	{/if}
</div>
