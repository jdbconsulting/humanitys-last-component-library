<script lang="ts">
	let { size = 32 }: { size?: number } = $props();
</script>

<!--
  JD Brinton Consulting, Inc. logo mark.
  Replicated 1:1 from jdbrinton.consulting so the two sites read as one family.
  Navy rounded square + amber lightning bolt.
-->
<svg
	viewBox="0 0 32 32"
	width={size}
	height={size}
	aria-hidden="true"
	xmlns="http://www.w3.org/2000/svg"
>
	<rect width="32" height="32" rx="6" fill="#111b30" />
	<path d="M18 4L10 18h6l-2 10 8-14h-6l2-10z" fill="#f59e0b" />
</svg>
