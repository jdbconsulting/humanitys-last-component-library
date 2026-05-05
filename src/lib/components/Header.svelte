<script lang="ts">
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { pathnameInApp } from '$lib/pathname-in-app';
	import JdbcMark from './JdbcMark.svelte';

	const links: { href: '/' | '/docs/' | '/configure/'; label: string }[] = [
		{ href: '/', label: 'Home' },
		{ href: '/docs/', label: 'Docs' },
		{ href: '/configure/', label: 'Configure' }
	];

	function pathFromNavHref(href: string): string {
		const t = href.replace(/\/+$/, '');
		return t.length === 0 ? '/' : t;
	}

	function isActive(href: string): boolean {
		const cur = pathnameInApp(page.url.pathname);
		if (href === '/') return cur === '/';
		if (href === '/docs/') return cur === '/docs' || cur.startsWith('/docs/');
		return cur === pathFromNavHref(href);
	}
</script>

<header class="sticky top-0 z-40 border-b border-ink-200/80 bg-white/95 backdrop-blur-md">
	<div class="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
		<div class="flex items-center gap-4">
			<a href={resolve('/')} class="group flex items-center gap-3" aria-label="HLCL home">
				<span
					class="flex h-9 w-9 items-center justify-center rounded-lg bg-navy-900 text-ink-50 shadow-sm transition group-hover:bg-navy-800"
				>
					<svg
						viewBox="0 0 24 24"
						class="h-5 w-5"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
					>
						<rect x="2" y="9" width="20" height="6" rx="1" />
						<rect x="6" y="6" width="2" height="12" />
						<rect x="16" y="6" width="2" height="12" />
					</svg>
				</span>
				<span class="flex flex-col leading-tight">
					<span class="text-xs font-semibold tracking-[0.18em] text-ink-500 uppercase">HLCL</span>
					<span class="text-sm font-semibold text-ink-900">Humanity's Last Component Library</span>
				</span>
			</a>

			<a
				href="https://jdbrinton.consulting/tools"
				target="_blank"
				rel="noopener noreferrer"
				class="group hidden items-center gap-2 border-l border-ink-200 py-1 pl-4 sm:flex"
				title="A JD Brinton Consulting, Inc. tool — visit jdbrinton.consulting"
			>
				<JdbcMark size={20} />
				<span class="flex flex-col leading-tight">
					<span class="text-[10px] font-medium tracking-wider text-ink-400 uppercase"
						>A tool by</span
					>
					<span class="text-xs font-semibold text-ink-700 transition group-hover:text-navy-900">
						JD Brinton Consulting
					</span>
				</span>
			</a>
		</div>

		<nav class="flex items-center gap-1">
			{#each links as link (link.href)}
				<a
					href={resolve(link.href)}
					class={[
						'rounded-md px-3 py-1.5 text-sm font-medium transition',
						isActive(link.href)
							? 'bg-navy-900 text-white'
							: 'text-ink-600 hover:bg-ink-100 hover:text-ink-900'
					]}
				>
					{link.label}
				</a>
			{/each}
			<a
				class="ml-2 rounded-md border border-ink-200 px-3 py-1.5 text-sm font-medium text-ink-700 transition hover:border-ink-300 hover:bg-ink-100"
				href="https://github.com/jdbconsulting/humanitys-last-component-library"
				target="_blank"
				rel="noopener noreferrer"
			>
				GitHub
			</a>
		</nav>
	</div>
</header>
