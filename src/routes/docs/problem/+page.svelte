<svelte:head>
	<title>The problem · Docs · HLCL</title>
</svelte:head>

<h1 class="text-3xl font-bold tracking-tight text-ink-900">The problem</h1>

<div class="prose-docs mt-8 space-y-5 text-ink-700">
	<p>
		Most vendor and “house” passive libraries are <strong class="text-ink-900"
			>not built as first-class IPC land-pattern products</strong
		>. Pads are often traced from old app notes, copied between revisions, or tuned by eye. The
		result is predictable: the same package outline with mutually incompatible pad stacks across
		libraries, silks that fight assembly, and mask rules that nobody can explain.
	</p>
	<p>
		Even when a library claims “IPC” in the name, it is frequently <strong class="text-ink-900"
			>incomplete or internally inconsistent</strong
		>: density levels mixed without documentation, tolerance terms missing, thermal spokes rounded
		off differently per part family, and 3D bodies that do not match the soldermask opening you are
		actually fabricating.
	</p>
	<p>
		<strong class="text-ink-900">Mistakes compound</strong> because passives are high copy count. A wrong
		zero-degree chip pad does not stay isolated—it propagates through BoM-driven updates, design variants,
		and migration templates. Teams learn not to trust the library, so every project reopens the same arguments
		about pad width and heel fillet.
	</p>
	<p>
		HLCL takes the opposite stance: <strong class="text-ink-900">one auditable rules engine</strong
		>, explicit IPC-7351B inputs, and generated outputs so you can diff what changed and why—instead
		of hand-editing copper in a thousand cells.
	</p>
</div>
