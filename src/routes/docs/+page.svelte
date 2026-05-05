<script lang="ts">
	import { resolve } from '$app/paths';
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
