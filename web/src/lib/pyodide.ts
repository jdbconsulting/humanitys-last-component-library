// Lightweight Pyodide loader. Loads from the official jsdelivr CDN on first use,
// wires stdout/stderr into the app's reactive console, and caches the runtime so
// subsequent `runHelloWorld` style calls reuse the same interpreter.
//
// We import the CDN script via a dynamic <script> tag so the build output
// doesn't try to resolve `pyodide` as an npm dep. The site stays static.

import { consoleLog } from './console.svelte';

const PYODIDE_VERSION = '0.28.0';
const PYODIDE_BASE = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

/** Subset of the Pyodide runtime API surface we actually use. */
export interface PyodideRuntime {
	runPython: (code: string) => unknown;
	runPythonAsync: (code: string) => Promise<unknown>;
	setStdout: (opts: { batched: (s: string) => void }) => void;
	setStderr: (opts: { batched: (s: string) => void }) => void;
	loadPackage: (names: string | string[]) => Promise<void>;
	version: string;
}

declare global {
	interface Window {
		loadPyodide?: (opts: { indexURL: string }) => Promise<PyodideRuntime>;
	}
}

let pyodidePromise: Promise<PyodideRuntime> | null = null;
let scriptLoaded = false;

function loadCdnScript(): Promise<void> {
	if (scriptLoaded) return Promise.resolve();
	if (typeof document === 'undefined')
		return Promise.reject(new Error('Pyodide requires a browser'));

	return new Promise((resolve, reject) => {
		const existing = document.querySelector<HTMLScriptElement>(
			`script[data-pyodide="${PYODIDE_VERSION}"]`
		);
		if (existing) {
			scriptLoaded = true;
			resolve();
			return;
		}
		const tag = document.createElement('script');
		tag.src = `${PYODIDE_BASE}pyodide.js`;
		tag.async = true;
		tag.dataset.pyodide = PYODIDE_VERSION;
		tag.onload = () => {
			scriptLoaded = true;
			resolve();
		};
		tag.onerror = () => reject(new Error('Failed to load pyodide.js from CDN'));
		document.head.appendChild(tag);
	});
}

/**
 * Lazily-construct the Pyodide runtime. Repeated calls return the same instance.
 * Streams stdout/stderr into `consoleLog`.
 */
export async function getPyodide(): Promise<PyodideRuntime> {
	if (pyodidePromise) return pyodidePromise;

	pyodidePromise = (async () => {
		consoleLog.system(`Loading Pyodide ${PYODIDE_VERSION} from CDN…`);
		await loadCdnScript();

		if (!window.loadPyodide) {
			throw new Error('window.loadPyodide is undefined after script load');
		}

		const py = await window.loadPyodide({ indexURL: PYODIDE_BASE });

		py.setStdout({
			batched: (s: string) => {
				if (s.length > 0) consoleLog.stdout(s);
			}
		});
		py.setStderr({
			batched: (s: string) => {
				if (s.length > 0) consoleLog.stderr(s);
			}
		});

		consoleLog.system(`Pyodide ${py.version} ready.`);
		return py;
	})();

	try {
		return await pyodidePromise;
	} catch (err) {
		pyodidePromise = null;
		throw err;
	}
}

/** Reset the cached runtime — used when the user wants a fresh interpreter. */
export function resetPyodide(): void {
	pyodidePromise = null;
}
