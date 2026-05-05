import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import { hlclBuildAssets } from './vite/plugins/hlcl-build-assets';

export default defineConfig({
	server: { host: true, allowedHosts: ['localhost', '127.0.0.1', '0.0.0.0'] },
	plugins: [hlclBuildAssets(), tailwindcss(), sveltekit()]
});
