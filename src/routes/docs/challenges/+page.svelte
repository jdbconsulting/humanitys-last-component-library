<svelte:head>
	<title>Challenges · Docs · HLCL</title>
</svelte:head>

<h1 class="text-3xl font-bold tracking-tight text-ink-900">Challenges</h1>

<div class="prose-docs mt-8 space-y-5 text-ink-700">
	<p>
		Shipping a browser-native Altium library generator meant <strong class="text-ink-900"
			>reverse engineering and stabilizing Altium’s footprint library formats</strong
		>—not just reading public marketing PDFs, but producing byte-level artifacts that open cleanly
		in modern Altium builds, round-trip through migration, and preserve the parametric links teams
		expect.
	</p>
	<p>
		<strong class="text-ink-900">IPC-7351B is precise.</strong> Density levels, material conditions, fabrication
		tolerances, and toe/heel/side fillets all interact. A generator has to apply the same round-off and
		guard-band rules every time, or two “identical” runs will diverge. We invested in testable math and
		explicit configuration so “what we meant” is not trapped in a spreadsheet.
	</p>
	<p>
		<strong class="text-ink-900">The browser is a constraint and a feature.</strong> Running a Python
		pipeline in WebAssembly (Pyodide) avoids shipping a desktop agent, but it demands careful packaging,
		deterministic builds, and honest progress reporting when CPU and memory are bounded. Everything you
		configure stays on your machine; the hard part is still making the engine fast enough to feel instant
		for real projects.
	</p>
	<p>
		Finally, <strong class="text-ink-900">vendor data drifts.</strong> Families age out, part numbers
		split, and ordering codes change. HLCL encodes families and parameters so updates are data-driven
		instead of a manual library merge every quarter.
	</p>
</div>
