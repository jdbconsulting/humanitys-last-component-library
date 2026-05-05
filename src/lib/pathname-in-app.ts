import { base } from '$app/paths';

/** Normalized pathname within the mounted base (GitHub Pages `paths.base`). */
export function pathnameInApp(fullPathname: string): string {
	const b = base.replace(/\/$/, '');
	let p = fullPathname;
	if (b && (p === b || p.startsWith(`${b}/`))) {
		p = p.slice(b.length) || '/';
	}
	if (!p.startsWith('/')) p = `/${p}`;
	return p.replace(/\/+$/, '') || '/';
}
