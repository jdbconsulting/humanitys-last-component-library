/**
 * Normalise user-facing configuration labels into a cross-platform-safe file stem
 * (no directory separators, no control chars, suitable for `*.json` downloads).
 */
const CONTROL_AND_ILLEGAL = /[\u0000-\u001f<>:"/\\|?*]/g;

/** Windows reserved device names (case-insensitive), without extension. */
const WIN_RESERVED = /^(con|prn|aux|nul|com[1-9]|lpt[1-9])$/i;

export function sanitizeConfigFilenameStem(raw: string, fallback = 'hlcl-build'): string {
	let s = raw.trim();
	if (s.toLowerCase().endsWith('.json')) {
		s = s.slice(0, -'.json'.length).trim();
	}
	s = s.replace(CONTROL_AND_ILLEGAL, '');
	s = s.toLowerCase();
	s = s.replace(/[^a-z0-9._-]+/g, '-');
	s = s.replace(/^-+|-+$/g, '');
	s = s.replace(/^\.+|\.+$/g, '');
	if (!s) return fallback;
	const base = s.includes('.') ? s.slice(0, s.indexOf('.')) : s;
	if (WIN_RESERVED.test(base)) return `${s}-file`;
	return s;
}
