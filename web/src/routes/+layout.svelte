<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import { appState } from '$lib/state.svelte';

	let { children } = $props();

	// Hydrate from localStorage once on mount, then persist on every change.
	// Both effects only run in the browser by definition.
	$effect(() => {
		appState.hydrate();
	});

	$effect(() => {
		// Touch each top-level slice so the effect tracks reassignments;
		// `persist()` walks the proxies via `$state.snapshot`, picking up
		// deep mutations as well.
		void appState.families;
		void appState.project;
		void appState.build;
		void appState.crosslinks;
		// Order matters: detect customisation FIRST (may clear activePresetId),
		// then persist the resulting snapshot.
		appState.detectCustomisation();
		appState.persist();
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Humanity's Last Component Library</title>
</svelte:head>

<div class="flex min-h-screen flex-col">
	<Header />
	<main class="flex flex-1 flex-col">
		{@render children()}
	</main>
	<Footer />
</div>
