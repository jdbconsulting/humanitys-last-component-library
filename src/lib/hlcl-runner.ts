/**
 * Browser-side driver for the Python HLCL build pipeline.
 *
 * Once Pyodide is loaded, the runner takes care of:
 *
 *   1. Lazily fetching `static/hlcl-build-inputs.tgz` (regenerated at site
 *      build time by `vite/plugins/hlcl-build-assets.ts` from the project-root
 *      `hlcl/` source tree) and extracting it into Pyodide's in-memory FS at
 *      `/hlcl/`.
 *   2. Serialising the active ``BuildConfig`` to ``/hlcl/build-config.json``
 *      so the Python side picks it up via ``build.discover(config_path=…)``
 *      — exactly the same code path as ``python build.py --config <path>``
 *      from the CLI.
 *   3. Running ``build.discover() / build.build_all()`` while yielding to
 *      the JS event loop between targets — Pyodide runs synchronously on
 *      the main thread, so the explicit ``await asyncio.sleep(0)`` after
 *      each target is what actually flushes the buffered stdout to
 *      ``consoleLog`` and lets the UI repaint mid-build. The runner skips
 *      every target whose ``cfg.is_target_enabled(...)`` predicate is
 *      false, so disabled families / artifacts cost ~zero time per click.
 *   4. Walking `/hlcl/build/output/` to enumerate the produced artifacts and
 *      handing each file's bytes back to JS (via ``pyodide.FS.readFile``) so
 *      they can be downloaded individually or zipped.
 */

import { base } from '$app/paths';
import { consoleLog } from './console.svelte';
import { getPyodide, type PyodideRuntime } from './pyodide';
import type { BuildConfig } from './schema';

/** Where the Vite plugin emits the build-inputs tarball. */
const TARBALL_URL = `${base}/hlcl-build-inputs.tgz`;

/** Pyodide-side absolute path the tarball is unpacked to. */
const HLCL_ROOT = '/hlcl';

/** Where the per-run BuildConfig JSON is staged inside Pyodide's MEMFS.
 * `build.py --config <path>` and `build.build_all(config_path=...)` both
 * accept this exact filename. */
const CONFIG_PATH = `${HLCL_ROOT}/build-config.json`;

/** Path the source tarball is staged at before extraction. */
const TARBALL_STAGE = '/tmp/hlcl-build-inputs.tgz';

let sourcesMounted = false;

export interface BuildOutputFile {
	/** Path relative to `/hlcl/build/output/` (always uses `/`). */
	path: string;
	/** Size in bytes (from MEMFS stat). */
	size: number;
}

/**
 * Build-derived stats computed by `hlcl/build_stats.py` after a
 * successful `runBuild`. Surfaced at the top of the configure page;
 * persisted alongside a hash of the BuildConfig that produced them so
 * we can fade them to "stale" the moment the user edits anything
 * downstream.
 *
 * Only the two numbers that need a build to compute live here. The
 * "Families" banner cell is derived live from the BuildConfig in TS
 * (it's just the count of enabled families) and never goes stale.
 */
export interface BuildStats {
	/** Total MPN rows across every emitted vendor `.xls` workbook. */
	components: number;
	/**
	 * Distinct footprint definitions in the priority-resolved
	 * `house-footprints.json`.
	 */
	unique_footprints: number;
}

/**
 * Pure-Python runtime deps that `build.py` needs. Installed via micropip on
 * first mount. Mirrors `requirements.txt` at the repo root.
 *
 *   * `xlwt` — vendor scripts emit Excel 97-2003 workbooks (.xls).
 *   * `xlrd` — `hlcl/build_stats.py` reads those .xls files back to count
 *              MPN rows for the configurator's library-stats banner.
 *              xlrd 2.x dropped `.xlsx` support but kept `.xls`, which is
 *              exactly the format we emit, so no version pin is needed.
 */
const PYTHON_REQUIREMENTS = ['xlwt>=1.3.0', 'xlrd>=2.0.0'];

let depsInstalled = false;

/**
 * Install the pure-Python packages `build.py` needs (just `xlwt` today) via
 * micropip. Idempotent — micropip itself caches downloads, but we also gate
 * on a module-level flag to skip the round-trip on subsequent calls.
 */
async function installPythonRequirements(py: PyodideRuntime): Promise<void> {
	if (depsInstalled) return;
	consoleLog.system(`Installing Python deps: ${PYTHON_REQUIREMENTS.join(', ')}…`);
	await py.loadPackage('micropip');
	const reqsJson = JSON.stringify(PYTHON_REQUIREMENTS);
	await py.runPythonAsync(`
import json, micropip
reqs = json.loads(${pyStr(reqsJson)})
await micropip.install(reqs)
print(f"micropip: installed {', '.join(reqs)}", flush=True)
`);
	depsInstalled = true;
}

/**
 * Make the HLCL source tree available to Pyodide. Idempotent — subsequent
 * calls are no-ops unless `force` is true. Streams progress messages to the
 * shared console.
 */
export async function mountHlclSources(force = false): Promise<void> {
	if (sourcesMounted && !force) return;
	const py = await getPyodide();

	await installPythonRequirements(py);

	consoleLog.system(`Fetching HLCL build inputs from ${TARBALL_URL}…`);
	const resp = await fetch(TARBALL_URL);
	if (!resp.ok) {
		throw new Error(`Failed to fetch ${TARBALL_URL}: HTTP ${resp.status}`);
	}
	const bytes = new Uint8Array(await resp.arrayBuffer());
	consoleLog.system(
		`Got ${(bytes.length / 1024 / 1024).toFixed(2)} MiB tarball; unpacking into ${HLCL_ROOT}/…`
	);

	if (!py.FS.analyzePath('/tmp').exists) py.FS.mkdir('/tmp');
	py.FS.writeFile(TARBALL_STAGE, bytes);

	await py.runPythonAsync(`
import os, shutil, tarfile, sys
if os.path.isdir(${pyStr(HLCL_ROOT)}):
    shutil.rmtree(${pyStr(HLCL_ROOT)})
os.makedirs(${pyStr(HLCL_ROOT)}, exist_ok=True)
with tarfile.open(${pyStr(TARBALL_STAGE)}, 'r:gz') as tf:
    # filter='data' suppresses the Python 3.14 DeprecationWarning and is the
    # safest extraction policy: rejects absolute paths, parent-directory
    # traversal, and unusual file types. Available since 3.12 (Pyodide ships
    # 3.13+).
    tf.extractall(${pyStr(HLCL_ROOT)}, filter='data')
# Wipe a previously imported build module so a fresh tree gets re-discovered.
sys.modules.pop('build', None)
print(f"Mounted {len(os.listdir(${pyStr(HLCL_ROOT)}))} top-level entries at ${HLCL_ROOT}", flush=True)
`);

	sourcesMounted = true;
}

/**
 * The Python wrapper that drives `build.build_all()` while explicitly yielding
 * between targets so JS can flush `consoleLog` and render. Stays string-y
 * (rather than living in a `.py` file in MEMFS) so we don't have to ship it
 * inside the build-inputs tarball.
 *
 * Two parametrised paths are interpolated:
 *
 *   * ``HLCL_ROOT`` — where the build-inputs tarball was unpacked. Becomes
 *     the ``root`` argument of ``build.discover()``.
 *   * ``CONFIG_PATH`` — where the per-run BuildConfig JSON has been written
 *     by ``writeBuildConfig`` just before this runner is invoked. Becomes
 *     the ``config_path`` argument of ``build.discover()``, the same code
 *     path the CLI takes via ``python build.py --config <path>``.
 *
 * Vendor / house generator scripts write their progress logs via
 * ``print(..., file=sys.stderr)`` — a holdover from the Make-driven era when
 * stderr was the natural channel for "loud" progress so stdout could be piped.
 * Under Pyodide that lights up the ``setStderr`` handler and renders every
 * line as a red ``ERR`` row in the UI console. We redirect ``sys.stderr`` to
 * ``sys.stdout`` for the duration of the build so those status writes flow
 * through the stdout handler instead. Real exceptions still surface via the
 * rejected ``runPythonAsync`` promise (caught by ``onRunBuild`` in
 * ``GenerateTab.svelte``) and are rendered as a single red ``ERR`` row, which
 * is the visual emphasis we actually want for failures.
 */
const RUNNER_SOURCE = `
import asyncio, os, sys, importlib

if ${pyStr(HLCL_ROOT)} not in sys.path:
    sys.path.insert(0, ${pyStr(HLCL_ROOT)})

# Wipe every module that came out of HLCL_ROOT before this run so the
# new BuildConfig (written to ${CONFIG_PATH} just before this runner
# fires) is captured by *every* vendor / house import. This includes:
#   * 'build'                       — registry singleton
#   * '_config'                     — config singleton
#   * '_common', '_panasonic_common', etc. (vendor shared helpers
#     under hlcl/vendors/) — they all 'import _config' at module
#     scope, capturing a *binding* to the _config module object,
#     which becomes stale the moment we pop _config but leave them
#     cached. That stale binding is precisely what made per-family
#     density overrides silently fall back to the previous run's
#     config on subsequent build clicks.
#   * '_hlcl_loaded__*'             — every dynamically-loaded
#     _build.py / generator script.
_hlcl_root_real = os.path.realpath(${pyStr(HLCL_ROOT)})
for mod_name in list(sys.modules):
    mod = sys.modules.get(mod_name)
    if mod is None:
        continue
    mod_file = getattr(mod, '__file__', None) or ''
    if (
        mod_name in ('build', '_config')
        or mod_name.startswith('_hlcl_loaded__')
        or (mod_file and os.path.realpath(mod_file).startswith(_hlcl_root_real + os.sep))
    ):
        sys.modules.pop(mod_name, None)
import _config  # noqa: E402
import build  # noqa: E402

async def _run(root, config_path):
    cfg = build.discover(root=root, config_path=config_path)
    seen = set()
    # Terminal targets the dep walk fans out from. 'standards' is a
    # leaf with no downstream consumer of its own, so we list it
    # explicitly alongside the .PcbLib / .SchLib terminals -- otherwise
    # toggling either standards artifact on would have no effect.
    for terminal in ('house-pcblib', 'house-schlib', 'standards'):
        if terminal not in build._REGISTRY:
            continue
        for n in build._resolve_deps(terminal):
            if n in seen:
                continue
            t = build._REGISTRY[n]
            if t.cli_only:
                continue
            if not cfg.is_target_enabled(n, t.kind):
                print(f"--> skipping {t.name} (disabled by config)", flush=True)
                seen.add(n)
                continue
            print(f"==> {t.name}", flush=True)
            await asyncio.sleep(0)  # flush console + repaint
            t.runner()
            seen.add(n)
    return [n for n in seen if build._REGISTRY[n].kind != 'aggregate']

# Funnel "loud progress" writes to stdout for the duration of this build so
# they show as OUT (white) rather than ERR (red) in the console. Real Python
# exceptions still propagate up via Pyodide's promise rejection.
_orig_stderr = sys.stderr
sys.stderr = sys.stdout
try:
    ran = await _run(${pyStr(HLCL_ROOT)}, ${pyStr(CONFIG_PATH)})
    print(f"Build complete. Ran {len(ran)} targets: {', '.join(sorted(ran))}", flush=True)
finally:
    sys.stderr = _orig_stderr
`;

/**
 * Serialise ``cfg`` to JSON and write it to ``CONFIG_PATH`` in MEMFS so
 * ``build.discover(config_path=CONFIG_PATH)`` picks it up. Validation is
 * performed Python-side by ``hlcl/_config.from_dict``; a malformed config
 * surfaces as the rejected ``runPythonAsync`` promise from ``runBuild``.
 */
async function writeBuildConfig(py: PyodideRuntime, cfg: BuildConfig): Promise<void> {
	const json = JSON.stringify(cfg, null, 2);
	if (!py.FS.analyzePath(HLCL_ROOT).exists) py.FS.mkdir(HLCL_ROOT);
	py.FS.writeFile(CONFIG_PATH, json);
}

/**
 * Run `build.build_all(root='/hlcl', config_path='/hlcl/build-config.json')`
 * end-to-end. Mounts the source tree lazily on first call. The caller passes
 * the live ``BuildConfig`` from the configurator UI; we serialise it to JSON,
 * stage it in MEMFS, and let the Python side validate + apply it (same code
 * path as ``python build.py --config <path>`` from the CLI). Stdout / stderr
 * stream into ``consoleLog`` via the handlers wired up in ``pyodide.ts``.
 */
export async function runBuild(cfg: BuildConfig): Promise<void> {
	await mountHlclSources();
	const py = await getPyodide();
	await writeBuildConfig(py, cfg);
	consoleLog.system(`Running build with config (${HLCL_ROOT}/build-config.json) …`);
	await py.runPythonAsync(RUNNER_SOURCE);
}

/**
 * Wipe `/hlcl/build/` so the next build starts from a clean slate. Called
 * before `runBuild()` whenever the user clicks "Run build" so a previously-
 * generated artifact for a now-disabled family can't sneak into the output.
 */
export async function cleanBuild(): Promise<void> {
	const py = await getPyodide();
	await py.runPythonAsync(`
import os, shutil
build_dir = os.path.join(${pyStr(HLCL_ROOT)}, 'build')
if os.path.isdir(build_dir):
    shutil.rmtree(build_dir)
`);
}

/**
 * Walk `/hlcl/build/output/` and return one entry per artifact file, sorted
 * by path. Returns an empty array if the directory doesn't exist (e.g.
 * before the first build).
 */
export async function listBuildOutputs(): Promise<BuildOutputFile[]> {
	const py = await getPyodide();
	const result = await py.runPythonAsync(`
import json, os
root = os.path.join(${pyStr(HLCL_ROOT)}, 'build', 'output')
out = []
if os.path.isdir(root):
    for dirpath, _, filenames in os.walk(root):
        for f in sorted(filenames):
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, root).replace(os.sep, '/')
            out.append({'path': rel, 'size': os.path.getsize(full)})
out.sort(key=lambda e: e['path'])
json.dumps(out)
`);
	return JSON.parse(String(result)) as BuildOutputFile[];
}

/**
 * Walk the just-built `/hlcl/build/` tree and return the build-derived
 * banner stats — total component MPN rows (sum across every vendor
 * `.xls` workbook via xlrd) and distinct footprints in the merged
 * `house-footprints.json`. Errors raised by
 * `build_stats.compute_build_stats` (e.g. a corrupt .xls that xlrd
 * can't parse) bubble up as a rejected `runPythonAsync` promise so
 * the caller in `GenerateTab` can surface them via `consoleLog.error`.
 *
 * (The third banner cell, "Families", is read directly off the live
 * BuildConfig — see `+page.svelte` — so it doesn't ride along here.)
 */
export async function computeBuildStats(): Promise<BuildStats> {
	const py = await getPyodide();
	const result = await py.runPythonAsync(`
import json, sys
if ${pyStr(HLCL_ROOT)} not in sys.path:
    sys.path.insert(0, ${pyStr(HLCL_ROOT)})
import build_stats
json.dumps(build_stats.compute_build_stats(${pyStr(HLCL_ROOT)}))
`);
	return JSON.parse(String(result)) as BuildStats;
}

/** Read a single artifact's raw bytes out of MEMFS for download / zipping. */
export async function readOutputBytes(relPath: string): Promise<Uint8Array> {
	const py = await getPyodide();
	const data = py.FS.readFile(`${HLCL_ROOT}/build/output/${relPath}`);
	return data;
}

/**
 * Reset the runner so the next call re-fetches the tarball + reinstalls
 * Python deps. Used by the UI "Reset cache" affordance (alongside the
 * Pyodide runtime reset).
 */
export function resetSourcesMount(): void {
	sourcesMounted = false;
	depsInstalled = false;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Quote a JS string as a Python triple-quoted string for embedding in
 * `runPythonAsync` source. Escapes the four characters PEP-3101's repr
 * doesn't already cover.
 */
function pyStr(s: string): string {
	return JSON.stringify(s);
}

/** Type guard for callers that want to know if the runtime has the expected FS. */
export function hasFs(
	py: PyodideRuntime
): py is PyodideRuntime & { FS: NonNullable<PyodideRuntime['FS']> } {
	return typeof (py as PyodideRuntime).FS?.readFile === 'function';
}
