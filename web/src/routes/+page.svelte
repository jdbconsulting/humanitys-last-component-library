<script lang="ts">
	import { resolve } from '$app/paths';
	import JdbcMark from '$lib/components/JdbcMark.svelte';

	const features: { title: string; body: string; icon: string }[] = [
		{
			title: 'IPC-7351B compliant',
			body: 'Density-level pad math straight out of the standard, with auditable round-off and tolerance terms.',
			icon: 'shield'
		},
		{
			title: 'Pure-Python pipeline',
			body: 'Vendor databases, parametric STEP, and the .PcbLib are all generated from stdlib Python — runs in Pyodide.',
			icon: 'code'
		},
		{
			title: 'Browser-only',
			body: 'No Altium round-trip, no .NET SDK, no install. Configure, run, download.',
			icon: 'cloud'
		},
		{
			title: 'HLCL-001 drawing standard',
			body: 'Rounded-rect 25% pads, 0.05 mm mask expansion, embedded 3D, and minimum-sliver enforcement.',
			icon: 'ruler'
		}
	];

	const families: { kind: string; entries: string[] }[] = [
		{
			kind: 'Resistors',
			entries: [
				'Panasonic ERJ (thick film, 01005–0805)',
				'Panasonic ERA-A (thin film, 0201)',
				'Panasonic ERA-V/K (thin film hi-stab, 0402–0805)',
				'Panasonic ERA-P (thin film 500 V, 1206)',
				'Ohmite KDV (current-sense)'
			]
		},
		{
			kind: 'Capacitors',
			entries: [
				'Murata GCM (automotive MLCC)',
				'Murata GRM (commercial MLCC)',
				'Samsung CL (commercial MLCC)',
				'TDK CGA (automotive MLCC)'
			]
		},
		{
			kind: 'Ferrite beads',
			entries: ['Murata BLM (chip ferrite beads)']
		}
	];
</script>

<!-- Hero — mirrors jdbrinton.consulting's dark-navy + amber CTA pattern -->
<section class="relative overflow-hidden bg-navy-950">
	<div
		class="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(245,158,11,0.10),transparent_60%)]"
		aria-hidden="true"
	></div>
	<div
		class="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,rgba(59,130,246,0.06),transparent_55%)]"
		aria-hidden="true"
	></div>

	<div class="relative mx-auto max-w-7xl px-6 pt-20 pb-24 sm:pt-28 lg:pt-32">
		<!-- "Free" sticker — amber circular seal, hard-rotated via inline transform -->
		<div
			class="pointer-events-none absolute top-20 right-8 hidden select-none lg:block xl:top-24 xl:right-20"
			style="transform: rotate(14deg)"
			aria-hidden="true"
		>
			<div
				class="relative flex h-28 w-28 items-center justify-center rounded-full bg-accent-500 shadow-[0_12px_32px_-6px_rgba(245,158,11,0.50)] ring-[3px] ring-accent-300/30 ring-offset-[5px] ring-offset-navy-950 xl:h-32 xl:w-32"
			>
				<div class="absolute inset-2 rounded-full border-2 border-dashed border-navy-950/30"></div>
				<span class="relative text-4xl font-black tracking-tight text-navy-950 xl:text-[2.6rem]">
					FREE
				</span>
			</div>
		</div>

		<div class="mx-auto max-w-3xl text-center">
			<a
				href="https://jdbrinton.consulting/tools"
				target="_blank"
				rel="noopener noreferrer"
				class="group inline-flex items-center gap-2.5 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium text-ink-100 backdrop-blur transition hover:border-accent-500/40 hover:bg-white/10"
			>
				<JdbcMark size={14} />
				<span class="text-ink-300">A tool by</span>
				<span class="font-semibold text-white">JD Brinton Consulting, Inc.</span>
				<span class="text-accent-400 transition group-hover:translate-x-0.5">→</span>
			</a>

			<h1
				class="mt-6 text-4xl font-bold tracking-tight text-balance text-white sm:text-5xl lg:text-6xl lg:leading-[1.05]"
			>
				Stop fighting passive footprints.
			</h1>
			<p class="mt-6 text-lg text-pretty text-ink-300 sm:text-xl">
				<strong class="font-semibold text-white">Humanity's Last Component Library</strong> is a
				correct-by-construction Altium chip-passive library. Pick the vendor families you need,
				dial in the pad math and drawing standards, and generate the database, the
				<code class="rounded bg-white/10 px-1.5 py-0.5 font-mono text-sm text-accent-200"
					>.PcbLib</code
				>, and the parametric 3D models — all in your browser.
			</p>

			<div class="mt-10 flex flex-wrap items-center justify-center gap-3">
				<a
					href={resolve('/configure/')}
					class="inline-flex items-center gap-2 rounded-lg bg-accent-500 px-6 py-3 text-sm font-semibold text-navy-950 shadow-sm transition-all hover:bg-accent-400 hover:shadow-md"
				>
					Start configuring
					<svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
						<path
							fill-rule="evenodd"
							d="M10.293 4.293a1 1 0 011.414 0l5 5a1 1 0 010 1.414l-5 5a1 1 0 01-1.414-1.414L13.586 11H4a1 1 0 110-2h9.586l-3.293-3.293a1 1 0 010-1.414z"
							clip-rule="evenodd"
						/>
					</svg>
				</a>
				<a
					href="https://github.com/jdbrinton/be-done-with-it-passives"
					target="_blank"
					rel="noopener noreferrer"
					class="inline-flex items-center gap-2 rounded-lg px-6 py-3 text-sm font-semibold text-white ring-1 ring-white/20 transition hover:bg-white/10"
				>
					View on GitHub
				</a>
			</div>
		</div>
	</div>

	<!-- Bottom badge strip -->
	<div class="relative border-t border-white/10 bg-navy-950/60 backdrop-blur">
		<div class="mx-auto max-w-7xl px-6 py-4">
			<p
				class="text-center text-[11px] font-medium tracking-[0.2em] text-ink-400 uppercase sm:text-xs"
			>
				Open-source · IPC-7351B · Altium-compatible · Pure-stdlib Python · Pyodide
			</p>
		</div>
	</div>
</section>

<!-- Feature grid -->
<section class="border-b border-ink-200 bg-white">
	<div class="mx-auto grid max-w-7xl gap-px bg-ink-200 px-6 py-px sm:grid-cols-2 lg:grid-cols-4">
		{#each features as feature (feature.title)}
			<div class="bg-white p-8">
				<div
					class="flex h-10 w-10 items-center justify-center rounded-md bg-navy-900 text-white shadow-sm"
				>
					{#if feature.icon === 'shield'}
						<svg
							class="h-5 w-5"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							viewBox="0 0 24 24"
							><path
								d="M12 3l8 4v5c0 4.5-3.5 8.5-8 9-4.5-.5-8-4.5-8-9V7l8-4z"
								stroke-linecap="round"
								stroke-linejoin="round"
							/></svg
						>
					{:else if feature.icon === 'code'}
						<svg
							class="h-5 w-5"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							viewBox="0 0 24 24"
							><path
								d="M8 9l-4 3 4 3M16 9l4 3-4 3M14 5l-4 14"
								stroke-linecap="round"
								stroke-linejoin="round"
							/></svg
						>
					{:else if feature.icon === 'cloud'}
						<svg
							class="h-5 w-5"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							viewBox="0 0 24 24"
							><path
								d="M7 18a5 5 0 010-10 7 7 0 0113.92 1A4 4 0 0119 18H7z"
								stroke-linecap="round"
								stroke-linejoin="round"
							/></svg
						>
					{:else if feature.icon === 'ruler'}
						<svg
							class="h-5 w-5"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							viewBox="0 0 24 24"
							><path
								d="M3 9h18v6H3V9zm3 0v3m4-3v3m4-3v3m4-3v3"
								stroke-linecap="round"
								stroke-linejoin="round"
							/></svg
						>
					{/if}
				</div>
				<h3 class="mt-4 text-base font-semibold text-ink-900">{feature.title}</h3>
				<p class="mt-2 text-sm leading-relaxed text-ink-600">{feature.body}</p>
			</div>
		{/each}
	</div>
</section>

<!-- Vendor families section -->
<section class="bg-ink-50">
	<div class="mx-auto max-w-7xl px-6 py-20">
		<div class="mx-auto max-w-2xl text-center">
			<h2 class="text-3xl font-bold tracking-tight text-ink-900 sm:text-4xl">
				Vendor families included
			</h2>
			<p class="mt-4 text-base text-ink-600">
				Mix and match — every family ships with the JEDEC dimensions and tolerance bands needed
				for IPC-correct pad math.
			</p>
		</div>
		<div class="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
			{#each families as family (family.kind)}
				<div
					class="rounded-lg border border-ink-200 bg-white p-6 shadow-sm transition hover:border-ink-300 hover:shadow-md"
				>
					<div
						class="flex items-center gap-2 text-sm font-semibold tracking-wider text-navy-800 uppercase"
					>
						<span class="h-1.5 w-1.5 rounded-full bg-accent-500"></span>
						{family.kind}
					</div>
					<ul class="mt-4 space-y-2 text-sm text-ink-700">
						{#each family.entries as entry (entry)}
							<li class="flex items-start gap-2">
								<svg
									class="mt-0.5 h-4 w-4 shrink-0 text-accent-500"
									viewBox="0 0 20 20"
									fill="currentColor"
									><path
										fill-rule="evenodd"
										d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
										clip-rule="evenodd"
									/></svg
								>
								<span>{entry}</span>
							</li>
						{/each}
					</ul>
				</div>
			{/each}
		</div>

		<div class="mt-16 rounded-xl border border-ink-200 bg-white p-8 shadow-sm sm:p-12">
			<div class="grid gap-8 lg:grid-cols-2 lg:items-center">
				<div>
					<h3 class="text-2xl font-bold tracking-tight text-ink-900">Nine-step workflow</h3>
					<p class="mt-3 text-sm text-ink-600">
						The configurator walks you through every input the build needs. Your settings stay in
						the browser; nothing is uploaded.
					</p>
					<a
						href={resolve('/configure/')}
						class="mt-6 inline-flex items-center gap-2 rounded-md bg-navy-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-navy-800"
					>
						Begin →
					</a>
				</div>
				<ol class="space-y-3 text-sm text-ink-700">
					{#each ['Start from a preset (consumer, automotive, precision, …) or skip ahead.', 'Pick the vendor families and per-family overrides you want.', 'Edit the project-wide settings (IPC tolerances, HLCL drawing standards, STEP geometry).', 'Drag-reorder the footprint priority list — sets the authoritative source when vendors share an IPC identifier.', 'Define MPN/MFG cross-link substitutes for your BOM tools.', 'Preview the generated settings.toml and the ordered build plan.', 'Choose which build artifacts to emit (.xls, .DbLib, STEP, .PcbLib, …).', 'Run Python in your browser, watch the console, download a zip of the result.', 'Migrate to Altium — first-time Library Importer import, then script-driven footprint refresh for subsequent builds.'] as step, i (i)}
						<li class="flex items-start gap-3">
							<span
								class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-100 text-xs font-semibold text-accent-800"
								>{i + 1}</span
							>
							<span>{step}</span>
						</li>
					{/each}
				</ol>
			</div>
		</div>
	</div>
</section>

<!-- JDBC sponsor / "ready to build" CTA — mirrors the bottom-CTA on jdbrinton.consulting -->
<section class="relative overflow-hidden bg-navy-950 py-20 sm:py-24">
	<div
		class="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,rgba(245,158,11,0.08),transparent_60%)]"
		aria-hidden="true"
	></div>
	<div class="relative mx-auto max-w-7xl px-6">
		<div class="grid items-center gap-10 lg:grid-cols-[auto_1fr_auto]">
			<div class="hidden lg:block">
				<JdbcMark size={64} />
			</div>
			<div class="text-center lg:text-left">
				<p class="text-xs font-semibold tracking-[0.2em] text-accent-400 uppercase">
					Maintained by JDBC
				</p>
				<h2 class="mt-3 text-2xl font-bold tracking-tight text-white sm:text-3xl">
					Building something exceptional?
				</h2>
				<p class="mt-3 max-w-2xl text-base leading-relaxed text-ink-300">
					HLCL is one of several open-source tools we maintain at
					<a
						href="https://jdbrinton.consulting"
						target="_blank"
						rel="noopener noreferrer"
						class="font-medium text-white underline decoration-accent-500/60 underline-offset-4 hover:decoration-accent-400"
					>JD Brinton Consulting</a
					>. We partner with highly technical hardware companies — from chip-passive design through
					full system bring-up — to rapidly build proof-of-concepts.
				</p>
			</div>
			<div class="flex flex-wrap justify-center gap-3 lg:flex-col lg:items-stretch">
				<a
					href="https://jdbrinton.consulting/contact"
					target="_blank"
					rel="noopener noreferrer"
					class="inline-flex items-center justify-center gap-2 rounded-lg bg-accent-500 px-5 py-2.5 text-sm font-semibold text-navy-950 shadow-sm transition hover:bg-accent-400"
				>
					Talk to JDBC
				</a>
				<a
					href="https://jdbrinton.consulting/tools"
					target="_blank"
					rel="noopener noreferrer"
					class="inline-flex items-center justify-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold text-white ring-1 ring-white/20 transition hover:bg-white/10"
				>
					Other JDBC tools →
				</a>
			</div>
		</div>
	</div>
</section>
