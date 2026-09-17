<script lang="ts">
	import { resolve } from '$app/paths';
	import releases from '$lib/release-history.json';
	import { websiteVersion } from '$lib/website-version';
</script>

<svelte:head>
	<title>Docs · HLCL</title>
</svelte:head>

<h1 class="text-3xl font-bold tracking-tight text-ink-900">Documentation</h1>
<p class="mt-3 text-lg text-ink-600">
	Humanity's Last Component Library is documented in short, focused pages. Use the table of contents
	on the left (or above, on small screens) to jump in.
</p>

<ul class="mt-10 space-y-4 text-ink-700">
	<li>
		<a
			href={resolve('/docs/motivation/')}
			class="group block rounded-lg border border-ink-200 bg-ink-50/50 p-4 transition hover:border-navy-300 hover:bg-white"
		>
			<span class="font-semibold text-navy-900 group-hover:text-navy-800">Motivation</span>
			<span class="mt-1 block text-sm text-ink-600">
				Why this exists as a free offering from JD Brinton Consulting, Inc.
			</span>
		</a>
	</li>
	<li>
		<a
			href={resolve('/docs/problem/')}
			class="group block rounded-lg border border-ink-200 bg-ink-50/50 p-4 transition hover:border-navy-300 hover:bg-white"
		>
			<span class="font-semibold text-navy-900 group-hover:text-navy-800">The problem</span>
			<span class="mt-1 block text-sm text-ink-600">
				Why most passive libraries fail IPC expectations, ship mistakes, and burn design time.
			</span>
		</a>
	</li>
	<li>
		<a
			href={resolve('/docs/challenges/')}
			class="group block rounded-lg border border-ink-200 bg-ink-50/50 p-4 transition hover:border-navy-300 hover:bg-white"
		>
			<span class="font-semibold text-navy-900 group-hover:text-navy-800">Challenges</span>
			<span class="mt-1 block text-sm text-ink-600">
				What we had to figure out—Altium formats, fidelity, and running it all in the browser.
			</span>
		</a>
	</li>
	<li>
		<a
			href={resolve('/docs/how-it-works/')}
			class="group block rounded-lg border border-ink-200 bg-ink-50/50 p-4 transition hover:border-navy-300 hover:bg-white"
		>
			<span class="font-semibold text-navy-900 group-hover:text-navy-800">How it works</span>
			<span class="mt-1 block text-sm text-ink-600">
				Pure Python, auditable math, and a browser runtime—no install, no server-side build for your
				data.
			</span>
		</a>
	</li>
	<li>
		<a
			href={resolve('/docs/component-selection/')}
			class="group block rounded-lg border border-ink-200 bg-ink-50/50 p-4 transition hover:border-navy-300 hover:bg-white"
		>
			<span class="font-semibold text-navy-900 group-hover:text-navy-800">
				Component selection advice
			</span>
			<span class="mt-1 block text-sm text-ink-600">
				Practical guidance for choosing resistor, capacitor, and inductor families in HLCL.
			</span>
		</a>
	</li>
</ul>

<section
	id="revision-history"
	aria-labelledby="revision-history-heading"
	class="mt-12 scroll-mt-24 border-t border-ink-200 pt-8"
>
	<h2 id="revision-history-heading" class="text-2xl font-bold tracking-tight text-ink-900">
		Website revision history
	</h2>
	<p class="mt-3 text-ink-600">
		This build is <span class="font-mono text-sm text-ink-900">v{websiteVersion}</span>. Development
		versions include changes planned for the next release.
	</p>
	<div class="mt-6 space-y-6">
		{#each releases as release (release.version)}
			<article class="rounded-lg border border-ink-200 bg-ink-50/50 p-5">
				<div class="flex flex-wrap items-center gap-3">
					<h3 class="font-mono text-lg font-semibold text-ink-900">v{release.version}</h3>
					<span
						class="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-ink-600 ring-1 ring-ink-200"
					>
						{release.status === 'unreleased' ? 'Unreleased' : 'Released'}
					</span>
					{#if release.releasedOn}
						<time datetime={release.releasedOn} class="text-sm text-ink-500"
							>{release.releasedOn}</time
						>
					{/if}
				</div>
				<ul class="mt-4 list-disc space-y-2 pl-5 text-sm leading-relaxed text-ink-700">
					{#each release.changes as change (change)}
						<li>{change}</li>
					{/each}
				</ul>
			</article>
		{/each}
	</div>
</section>
