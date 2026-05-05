<script lang="ts">
	import JdbcMark from './JdbcMark.svelte';

	const year = new Date().getFullYear();
</script>

<footer class="border-t border-ink-200 bg-ink-50">
	<div class="mx-auto max-w-7xl px-4 py-10 sm:px-6 sm:py-12 lg:py-16">
		<div class="grid gap-8 sm:grid-cols-2 sm:gap-10 lg:grid-cols-4">
			<div class="lg:col-span-2">
				<a
					href="https://jdbrinton.consulting"
					target="_blank"
					rel="noopener noreferrer"
					class="flex items-center gap-3"
				>
					<JdbcMark size={36} />
					<span class="flex flex-col leading-tight">
						<span class="text-base font-bold tracking-tight text-ink-900">JDBC</span>
						<span class="text-xs text-ink-500">JD Brinton Consulting, Inc.</span>
					</span>
				</a>
				<p class="mt-4 max-w-md text-sm leading-relaxed text-ink-600">
					HLCL is a free, open-source tool from
					<a
						href="https://jdbrinton.consulting"
						target="_blank"
						rel="noopener noreferrer"
						class="font-medium text-ink-800 hover:text-navy-900">JD Brinton Consulting, Inc.</a
					> — engineering leadership for ambitious hardware teams. We partner with highly technical hardware
					companies to rapidly build proof-of-concepts.
				</p>
				<a
					href="https://jdbrinton.consulting/contact"
					target="_blank"
					rel="noopener noreferrer"
					class="mt-5 inline-flex items-center gap-2 rounded-md border border-ink-300 bg-white px-4 py-2 text-sm font-semibold text-ink-800 shadow-sm transition hover:border-navy-900 hover:text-navy-900"
				>
					Start a conversation with JDBC
					<svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
						<path
							fill-rule="evenodd"
							d="M10.293 4.293a1 1 0 011.414 0l5 5a1 1 0 010 1.414l-5 5a1 1 0 01-1.414-1.414L13.586 11H4a1 1 0 110-2h9.586l-3.293-3.293a1 1 0 010-1.414z"
							clip-rule="evenodd"
						/>
					</svg>
				</a>
			</div>

			<div>
				<h3 class="text-xs font-semibold tracking-[0.18em] text-ink-900 uppercase">HLCL</h3>
				<ul class="mt-4 space-y-2.5">
					<li>
						<a
							class="text-sm text-ink-600 transition hover:text-ink-900"
							href="https://github.com/jdbconsulting/humanitys-last-component-library"
							target="_blank"
							rel="noopener noreferrer">Source on GitHub</a
						>
					</li>
					<li>
						<a
							class="text-sm text-ink-600 transition hover:text-ink-900"
							href="https://github.com/jdbconsulting/humanitys-last-component-library/blob/main/README.md"
							target="_blank"
							rel="noopener noreferrer">Documentation</a
						>
					</li>
					<li>
						<a
							class="text-sm text-ink-600 transition hover:text-ink-900"
							href="https://github.com/jdbconsulting/humanitys-last-component-library/issues"
							target="_blank"
							rel="noopener noreferrer">Report an issue</a
						>
					</li>
				</ul>
			</div>

			<div>
				<h3 class="text-xs font-semibold tracking-[0.18em] text-ink-900 uppercase">JDBC</h3>
				<ul class="mt-4 space-y-2.5">
					<li>
						<a
							class="text-sm text-ink-600 transition hover:text-ink-900"
							href="https://jdbrinton.consulting/about"
							target="_blank"
							rel="noopener noreferrer">About</a
						>
					</li>
					<li>
						<a
							class="text-sm text-ink-600 transition hover:text-ink-900"
							href="https://jdbrinton.consulting/case-studies"
							target="_blank"
							rel="noopener noreferrer">Case studies</a
						>
					</li>
					<li>
						<a
							class="text-sm text-ink-600 transition hover:text-ink-900"
							href="https://jdbrinton.consulting/tools"
							target="_blank"
							rel="noopener noreferrer">Other tools</a
						>
					</li>
					<li>
						<a
							class="text-sm text-ink-600 transition hover:text-ink-900"
							href="https://jdbrinton.consulting/contact"
							target="_blank"
							rel="noopener noreferrer">Contact</a
						>
					</li>
				</ul>
			</div>
		</div>

		<div
			class="mt-12 flex flex-col gap-3 border-t border-ink-200 pt-6 text-xs text-ink-500 sm:flex-row sm:items-center sm:justify-between"
		>
			<p>
				© {year} JD Brinton Consulting, Inc. · HLCL released under the project's repository license. Generators
				run client-side in your browser via Pyodide; nothing is uploaded.
			</p>
			<a
				href="https://jdbrinton.consulting"
				target="_blank"
				rel="noopener noreferrer"
				class="font-medium text-ink-600 transition hover:text-ink-900"
			>
				jdbrinton.consulting →
			</a>
		</div>
	</div>
</footer>
