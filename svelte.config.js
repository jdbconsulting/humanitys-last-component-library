import adapter from '@sveltejs/adapter-static';

const dev = process.env.NODE_ENV !== 'production';
const base = dev ? '' : (process.env.BASE_PATH ?? '/be-done-with-it-passives');

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
