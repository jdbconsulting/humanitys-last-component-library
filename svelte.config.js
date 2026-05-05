import adapter from '@sveltejs/adapter-static';

const dev = process.env.NODE_ENV !== 'production';

// Production is served at the apex of the custom domain
// (`hlcl.jdbrinton.consulting`) via the CNAME shipped in `static/CNAME`,
// so the SvelteKit `base` is `''`. If you ever deploy to a path-prefixed
// GitHub Pages URL (e.g. `https://<owner>.github.io/<repo>/`), set
// `BASE_PATH=/<repo>` in the workflow env to bake that prefix into every
// emitted asset URL — leaving it unset will produce a bundle whose
// `/_app/...` paths only resolve at the apex.
const base = dev ? '' : (process.env.BASE_PATH ?? '');

/** @type {import('@sveltejs/kit').Config} */
const config = {
	compilerOptions: {
		// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
		runes: ({ filename }) => (filename.split(/[/\\]/).includes('node_modules') ? undefined : true)
	},
	kit: {
		adapter: adapter({
			pages: 'build',
			assets: 'build',
			fallback: '404.html',
			precompress: false,
			strict: true
		}),
		paths: { base, relative: false },
		prerender: { handleHttpError: 'warn' }
	}
};

export default config;
