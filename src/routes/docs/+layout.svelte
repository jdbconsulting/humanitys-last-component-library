<script lang="ts">
	import { page } from '$app/state';
	import { resolve } from '$app/paths';

	import { pathnameInApp } from '$lib/pathname-in-app';

	let { children } = $props();

	const sections = [
		{ href: '/docs/', label: 'Overview', hint: 'Table of contents' },
		{
			href: '/docs/motivation/',
			label: 'Motivation',
			hint: 'Why JD Brinton Consulting built HLCL'
		},
		{
			href: '/docs/problem/',
			label: 'The problem',
			hint: 'What goes wrong with typical footprint libraries'
		},
		{
			href: '/docs/challenges/',
			label: 'Challenges',
			hint: 'Altium formats, fidelity, shipping in-browser'
		},
		{
			href: '/docs/how-it-works/',
			label: 'How it works',
			hint: 'Python pipeline & browser runtime'
		},
		{
			href: '/docs/component-selection/',
			label: 'Component selection advice',
			hint: 'Which passives to use where'
		}
	] as const;

	type DocNavHref = (typeof sections)[number]['href'];

	const current = $derived(pathnameInApp(page.url.pathname));

	function pathFromDocHref(href: string): string {
		const t = href.replace(/\/+$/, '');
		return t.length === 0 ? '/' : t;
	}

	function navActive(href: DocNavHref): boolean {
		return current === pathFromDocHref(href);
	}
</script>

<div class="flex-1 border-b border-ink-200 bg-ink-50/40">
	<div
		class="mx-auto grid max-w-7xl gap-6 px-4 py-6 sm:gap-10 sm:px-6 sm:py-10 lg:grid-cols-[minmax(200px,17rem)_1fr] lg:gap-14 lg:py-14"
	>
		<nav aria-label="Documentation" class="lg:sticky lg:top-[4.75rem] lg:self-start">
			<p
				class="mb-4 text-[10px] font-semibold tracking-[0.2em] text-ink-400 uppercase"
				id="docs-toc-heading"
			>
				Docs
			</p>
			<ul
				class="flex flex-row gap-2 overflow-x-auto pb-2 lg:flex-col lg:gap-0 lg:space-y-0.5 lg:overflow-visible lg:pb-0"
				aria-labelledby="docs-toc-heading"
			>
				{#each sections as item (item.href)}
					<li class="flex-shrink-0">
						<a
							href={resolve(item.href)}
							class={[
								'block rounded-lg border px-3 py-2 transition lg:border-0 lg:px-2.5 lg:py-2',
								navActive(item.href)
									? 'border-navy-200 bg-white font-semibold text-navy-900 shadow-sm lg:border-transparent lg:bg-navy-900 lg:text-white lg:shadow-none'
									: 'border-transparent bg-white/70 text-ink-700 hover:border-ink-200 hover:bg-white hover:text-navy-900 lg:bg-transparent lg:hover:bg-white/80'
							]}
						>
							<span class="block text-sm">{item.label}</span>
							<span
								class="mt-0.5 block text-[11px] font-normal opacity-85 lg:text-xs {navActive(
									item.href
								)
									? 'text-ink-200 lg:text-ink-200'
									: 'text-ink-500'}"
							>
								{item.hint}
							</span>
						</a>
					</li>
				{/each}
			</ul>
		</nav>

		<article
			class="min-w-0 rounded-xl border border-ink-200/80 bg-white p-5 shadow-sm sm:p-8 lg:p-10"
		>
			{@render children()}
		</article>
	</div>
</div>
