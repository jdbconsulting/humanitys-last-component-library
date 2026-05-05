<svelte:head>
	<title>How it works · Docs · HLCL</title>
</svelte:head>

<h1 class="text-3xl font-bold tracking-tight text-ink-900">How it works</h1>

<div class="prose-docs mt-8 space-y-5 text-ink-700">
	<p>
		HLCL is built around a <strong class="text-ink-900">pure Python generation pipeline</strong>.
		Vendor spreadsheets, STEP assembly rules, IPC inputs, and drawing standards all flow through the
		same code paths whether you run locally or in the app—no hidden binaries and no opaque “trust
		us” footprints.
	</p>
	<p>
		In the web app that pipeline executes <strong class="text-ink-900"
			>inside your browser via Pyodide</strong
		> (CPython compiled to WebAssembly). You pick families, tune tolerances and HLCL-001 drafting rules,
		and trigger a build; downloads are emitted as ordinary files—the catalog database, PCB library, models,
		and related artifacts tailored to your configuration.
	</p>
	<p>
		Because generation is deterministic and parameterized, you can <strong class="text-ink-900"
			>treat HLCL like infrastructure</strong
		>: check in configuration, reproduce an old drop for a legacy design, or diff two outputs when a
		vendor releases a new density recommendation.
	</p>
	<p>
		The configure UI walks the workflow from presets through generate and migration cues so teams
		can adopt HLCL without a separate “library maintainer toolchain” beside Altium itself.
	</p>
</div>
