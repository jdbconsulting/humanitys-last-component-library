/**
 * HLCL build-assets Vite plugin.
 *
 * Generates four assets every time Vite starts (dev) or builds (prod):
 *
 *   1. `hlcl/build-config.schema.json` — a JSON Schema 2020-12 draft derived
 *      from the canonical Zod definition in `src/lib/schema.ts`. Sits next
 *      to `hlcl/build.py` so `python hlcl/build.py --config foo.json` (and
 *      any external `jsonschema` consumer) finds the same contract the web
 *      app uses.
 *
 *   2. `hlcl/factory-defaults.json` — a fully-populated default `BuildConfig`
 *      with every discovered family enabled, every artifact on, and the
 *      Zod-defined defaults for `settings.*`. `hlcl/build.py` falls back to
 *      this file when invoked without `--config`, so a fresh clone +
 *      `npm run dev` (or `npm run regen`) is all the setup needed to run
 *      a CLI build that mirrors the web app's "Factory defaults" preset.
 *
 *   3. `static/hlcl-build-inputs.tgz` — a gzipped POSIX tar of the subset of
 *      `hlcl/` that the in-browser Pyodide build actually needs: every
 *      Python source file, the vendor CSV inputs, the auto-generated
 *      `factory-defaults.json`, and the small `house/hardcoded/house.SchLib`
 *      blob. Reference PDFs, the coupon Altium project, generated `build/`
 *      output, and Python `__pycache__` directories are excluded so the
 *      tarball stays in the low single-digit MB range. Lives under
 *      `static/` so SvelteKit's adapter-static copies it into the deployed
 *      site, where the browser fetches it at `/hlcl-build-inputs.tgz`.
 *
 *   4. `src/lib/_generated/catalog.ts` — a TypeScript module re-exporting
 *      every `catalog.json` found under `hlcl/vendors/<mfg>/<family>/`,
 *      validated against `familyCatalogEntrySchema`. The Libraries tab
 *      imports this module directly, so dropping a new
 *      `vendors/<mfg>/<family>/catalog.json` file is all it takes for the
 *      configurator UI to grow. Vite's JSON loader inlines the data into
 *      the bundle at build time; no client-side fetch or tarball
 *      extraction is needed for the catalog.
 *
 *   The web app fetches the tarball lazily on the first "Run build" click,
 *   hands it to Pyodide, and unpacks it with stdlib `tarfile` into MEMFS
 *   under `/hlcl/` so `build.build_all(root='/hlcl')` can find everything
 *   exactly where it expects.
 *
 *   Dev-mode regeneration: the plugin re-emits all four assets at server
 *   start, then watches `hlcl/**` (and the schema source) for changes and
 *   re-emits as needed so the browser always sees the latest tree.
 */

import { createGzip } from 'node:zlib';
import { createWriteStream } from 'node:fs';
import { mkdir, readFile, stat, writeFile } from 'node:fs/promises';
import { dirname, join, posix, relative, resolve, sep } from 'node:path';
import { pipeline } from 'node:stream/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { glob } from 'tinyglobby';
import { pack as tarPack } from 'tar-stream';
import type { Plugin, ViteDevServer } from 'vite';

const HERE = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(HERE, '..', '..');
const HLCL_SRC = resolve(PROJECT_ROOT, 'hlcl');
const DOCS_STANDARDS_DIR = resolve(PROJECT_ROOT, 'docs', 'standards');
const SCHEMA_TS = resolve(PROJECT_ROOT, 'src', 'lib', 'schema.ts');
const SCHEMA_OUT = resolve(HLCL_SRC, 'build-config.schema.json');
const FACTORY_DEFAULTS_OUT = resolve(HLCL_SRC, 'factory-defaults.json');
const TARBALL_OUT = resolve(PROJECT_ROOT, 'static', 'hlcl-build-inputs.tgz');
const CATALOG_OUT = resolve(PROJECT_ROOT, 'src', 'lib', '_generated', 'catalog.ts');
const PRESETS_OUT = resolve(PROJECT_ROOT, 'src', 'lib', '_generated', 'presets.ts');
const VENDORS_DIR = resolve(HLCL_SRC, 'vendors');
const PRESETS_DIR = resolve(HLCL_SRC, 'presets');
const HLCL_REL = relative(PROJECT_ROOT, HLCL_SRC); // "hlcl"
const DOCS_STANDARDS_REL = relative(PROJECT_ROOT, DOCS_STANDARDS_DIR); // "docs/standards"

/**
 * Glob patterns (relative to `hlcl/`) that select build-relevant files.
 * Tracking text-only sources keeps the tarball gzip-friendly.
 */
const TARBALL_INCLUDE = [
	// Top-level orchestrator + the in-process config library that vendor /
	// house scripts import.
	'build.py',
	'_config.py',
	// Post-build statistics aggregator (reads build/output/*.xls + the
	// merged footprints JSON to populate the configurator's library
	// stats banner). Imported on-demand from the TS runner.
	'build_stats.py',
	// Auto-generated config artefacts the Pyodide-side build needs at runtime:
	//   - factory-defaults.json: fallback when no `--config` was passed.
	//   - build-config.schema.json: documentation / future jsonschema consumers.
	'factory-defaults.json',
	'build-config.schema.json',
	// All textual resources under `house/` that the Python pipeline opens at
	// runtime: scripts, opaque-text helpers like
	// `altium_pcblib/_library_params_template.txt` (read by writer.py), the
	// hardcoded SchLib. Keeping the list permissive prevents quiet
	// "FileNotFoundError" regressions when a new resource file is added next
	// to a script.
	'house/**/*.py',
	'house/**/*.txt',
	'house/**/*.json',
	'house/**/*.csv',
	'house/hardcoded/house.SchLib',
	// Vendor scripts, _build.py stubs, and the per-vendor CSV / TXT inputs
	// that drive them. Reference PDFs in `vendors/*/reference/` are excluded
	// by `TARBALL_EXCLUDE` below.
	'vendors/**/*.py',
	'vendors/**/*.csv',
	'vendors/**/*.txt'
];

/**
 * Files that live OUTSIDE `hlcl/` but still need to be in the tarball so
 * the in-browser Pyodide build can read them. Each entry maps an absolute
 * source path to the path it should land at INSIDE the tarball (which in
 * turn becomes an `/hlcl/<dest>` path after extraction).
 *
 * Currently: the HLCL-001 LaTeX / Markdown templates and the two
 * accompanying figures the standards build target renders. Living under
 * `docs/standards/` rather than `hlcl/` keeps the published-document
 * source where the rest of the project's documentation lives, while
 * still making them reachable from the in-process build.
 */
const TARBALL_EXTRAS: Array<{ src: string; dest: string }> = [
	{ src: resolve(DOCS_STANDARDS_DIR, 'standards.tex'), dest: 'standards/standards.tex' },
	{ src: resolve(DOCS_STANDARDS_DIR, 'standards.md'), dest: 'standards/standards.md' },
	{ src: resolve(DOCS_STANDARDS_DIR, 'example-symbol.png'), dest: 'standards/example-symbol.png' },
	{
		src: resolve(DOCS_STANDARDS_DIR, 'example-footprint.png'),
		dest: 'standards/example-footprint.png'
	}
];

/**
 * Patterns to drop AFTER `TARBALL_INCLUDE` matches. Tinyglobby supports `!`
 * negations directly; keeping them as a separate list documents intent.
 */
const TARBALL_EXCLUDE = [
	'**/__pycache__/**',
	'**/build/**',
	// Legacy hand-checked STEP models under `house/step/` — pre-dating the
	// parametric stepgen pipeline that emits fresh files into
	// `build/intermediate/step/`. Shipping them would inflate the tarball
	// for no payoff.
	'house/step/**',
	// Altium ~/History backup blobs.
	'house/**/History/**',
	'vendors/*/reference/**',
	// Samsung's two huge CSV catalogs are gitignored separately and not part
	// of the default build set; if a contributor checks them in locally we
	// still don't want them shipped to Pyodide.
	'vendors/samsung/General/**',
	'vendors/samsung/Automotive/**'
];

interface ParseResultLike<T> {
	ok: boolean;
	value?: T;
	errors?: string[];
}

interface DefaultBuildConfigLike {
	schema_version: string;
	families: Record<string, unknown>;
	settings: unknown;
	artifacts: unknown;
	crosslinks: unknown[];
}

/**
 * Snake-case mirror of the `FamilyCatalogEntry` runtime shape — kept loose
 * here because we only read a few fields and don't need the full Zod type
 * to land in the plugin (importing Zod just for nominal types would force
 * us to keep the Zod runtime in dev-deps).
 */
interface FamilyCatalogEntryLike {
	id: string;
	available_sizes: string[];
	options?: Array<{
		id: string;
		overrides_global?: boolean;
		control:
			| { kind: 'toggle'; default_value: boolean }
			| { kind: 'select'; default_value: string; choices: { id: string }[] }
			| { kind: 'multiselect'; default_value: string[]; choices: { id: string }[] }
			| { kind: 'number'; default_value: number }
			| { kind: 'text'; default_value: string };
	}>;
}

/**
 * Snake-case mirror of `PresetFile` — only the few fields the plugin
 * needs to sort and round-trip into the generated TS module.
 */
interface PresetFileLike {
	id: string;
	title: string;
	tagline: string;
	description: string;
	bullets: string[];
	sort_order: number;
	config: unknown;
}

interface SchemaModule {
	buildConfigSchema: unknown;
	BUILD_CONFIG_VERSION: string;
	parseFamilyCatalogEntry: (raw: unknown) => ParseResultLike<unknown>;
	parsePresetFile: (raw: unknown) => ParseResultLike<unknown>;
	defaultBuildConfig: () => DefaultBuildConfigLike;
}

/**
 * Load `src/lib/schema.ts` in-process via `tsx`'s ESM API. Avoids spawning a
 * child Node and avoids the heavyweight "spin up a sub-Vite to call
 * ssrLoadModule" pattern.
 */
async function loadSchemaModule(): Promise<SchemaModule> {
	const { tsImport } = (await import('tsx/esm/api')) as {
		tsImport: (specifier: string, parentURL: string) => Promise<unknown>;
	};
	const mod = (await tsImport(SCHEMA_TS, pathToFileURL(import.meta.url).href)) as SchemaModule;
	if (
		!mod.buildConfigSchema ||
		!mod.BUILD_CONFIG_VERSION ||
		typeof mod.parseFamilyCatalogEntry !== 'function' ||
		typeof mod.parsePresetFile !== 'function' ||
		typeof mod.defaultBuildConfig !== 'function'
	) {
		throw new Error(`schema.ts did not export the expected names: ${Object.keys(mod).join(', ')}`);
	}
	return mod;
}

/**
 * Emit `hlcl/build-config.schema.json` from the canonical Zod definition.
 * Uses Zod 4's native `z.toJSONSchema()` (no extra `zod-to-…` package
 * needed).
 */
async function emitSchemaSidecar(schemaMod: SchemaModule): Promise<void> {
	const z = (await import('zod')).default ?? (await import('zod'));
	const jsonSchema = (z as typeof import('zod')).toJSONSchema(schemaMod.buildConfigSchema as never);
	// Decorate with metadata that's not part of the Zod model itself but
	// helps both humans and tooling identify the file.
	const decorated = {
		...(jsonSchema as Record<string, unknown>),
		title: 'HLCL build configuration',
		description:
			'Canonical configuration consumed by the in-browser Pyodide build and (in a future revision) by `python build.py --config <file>`.',
		'x-schema-version': schemaMod.BUILD_CONFIG_VERSION,
		'x-generated-by': 'vite/plugins/hlcl-build-assets.ts'
	};
	await mkdir(dirname(SCHEMA_OUT), { recursive: true });
	await writeFile(SCHEMA_OUT, JSON.stringify(decorated, null, 2) + '\n', 'utf8');
}

/**
 * Walk `hlcl/` matching `TARBALL_INCLUDE` (minus `TARBALL_EXCLUDE`) and pack
 * every match into a gzipped USTAR tarball at `TARBALL_OUT`.
 *
 * Each entry's name is stored relative to the tarball root (e.g. `build.py`,
 * `vendors/murata/gcm/murata-gcm.py`) so that on the Python side
 * `tarfile.extractall('/hlcl')` lands the source tree at `/hlcl/...` —
 * exactly the layout `build.py` expects when called with `root='/hlcl'`.
 */
async function emitTarball(): Promise<{ files: number; bytes: number }> {
	const matches = await glob(TARBALL_INCLUDE, {
		cwd: HLCL_SRC,
		ignore: TARBALL_EXCLUDE,
		onlyFiles: true,
		dot: false
	});
	matches.sort();

	const pack = tarPack();
	const gzip = createGzip({ level: 9 });
	await mkdir(dirname(TARBALL_OUT), { recursive: true });
	const out = createWriteStream(TARBALL_OUT);

	const drain = pipeline(pack, gzip, out);

	let totalBytes = 0;
	let fileCount = 0;
	for (const rel of matches) {
		const abs = join(HLCL_SRC, rel);
		const st = await stat(abs);
		if (!st.isFile()) continue;
		const data = await readFile(abs);
		// Force POSIX `/` separators in the tar header even on Windows.
		const name = rel.split(sep).join(posix.sep);
		await new Promise<void>((res, rej) => {
			pack.entry(
				{ name, size: data.length, mode: 0o644, mtime: new Date(0), type: 'file' },
				data,
				(err) => (err ? rej(err) : res())
			);
		});
		totalBytes += data.length;
		fileCount += 1;
	}

	// Pack the project-root-sibling extras (currently the HLCL-001
	// standards templates + figures) at their target paths inside the
	// tarball. Missing sources are tolerated so a contributor working
	// from a checkout that strips the binary screenshots doesn't break
	// every other build asset.
	for (const extra of TARBALL_EXTRAS) {
		let st;
		try {
			st = await stat(extra.src);
		} catch {
			continue;
		}
		if (!st.isFile()) continue;
		const data = await readFile(extra.src);
		const name = extra.dest.split(sep).join(posix.sep);
		await new Promise<void>((res, rej) => {
			pack.entry(
				{ name, size: data.length, mode: 0o644, mtime: new Date(0), type: 'file' },
				data,
				(err) => (err ? rej(err) : res())
			);
		});
		totalBytes += data.length;
		fileCount += 1;
	}

	pack.finalize();
	await drain;
	return { files: fileCount, bytes: totalBytes };
}

/**
 * Scan `hlcl/vendors/<mfg>/<family>/catalog.json`, validate each file
 * against `familyCatalogEntrySchema` (loaded via the schema module), and
 * emit a typed TypeScript module at `src/lib/_generated/catalog.ts`.
 *
 * Validation errors fail the build loudly: a typo in catalog.json should
 * surface in the dev terminal immediately, not as a confusing runtime
 * error in the browser.
 */
async function emitCatalogModule(
	schemaMod: SchemaModule,
	logger?: ViteDevServer['config']['logger']
): Promise<{ entries: FamilyCatalogEntryLike[] }> {
	const matches = await glob(['*/*/catalog.json'], {
		cwd: VENDORS_DIR,
		onlyFiles: true,
		dot: false
	});
	matches.sort();

	const entries: unknown[] = [];
	const errors: string[] = [];
	for (const rel of matches) {
		const abs = join(VENDORS_DIR, rel);
		let raw: unknown;
		try {
			raw = JSON.parse(await readFile(abs, 'utf8'));
		} catch (err) {
			const msg = err instanceof Error ? err.message : String(err);
			errors.push(`${rel}: invalid JSON — ${msg}`);
			continue;
		}
		const result = schemaMod.parseFamilyCatalogEntry(raw);
		if (!result.ok || !result.value) {
			for (const e of result.errors ?? []) errors.push(`${rel}: ${e}`);
			continue;
		}
		entries.push(result.value);
	}

	if (errors.length > 0) {
		const summary = errors.map((e) => `  • ${e}`).join('\n');
		const msg = `[hlcl] catalog.json validation failed:\n${summary}`;
		if (logger) logger.error(msg);
		else console.error(msg);
		throw new Error(`${errors.length} catalog.json file(s) failed validation`);
	}

	// Stable ordering: by (subtype_order, kind, subtype_id, sort_order, id).
	// Kind ordering itself lives in `src/lib/libraries.ts` (closed taxonomy).
	type Sortable = {
		subtype_order: number;
		kind: string;
		subtype_id: string;
		sort_order: number;
		id: string;
	};
	(entries as Sortable[]).sort((a, b) => {
		if (a.kind !== b.kind) return a.kind.localeCompare(b.kind);
		if (a.subtype_order !== b.subtype_order) return a.subtype_order - b.subtype_order;
		if (a.subtype_id !== b.subtype_id) return a.subtype_id.localeCompare(b.subtype_id);
		if (a.sort_order !== b.sort_order) return a.sort_order - b.sort_order;
		return a.id.localeCompare(b.id);
	});

	// Diagnose subtype_label conflicts: two entries with the same subtype_id
	// but different labels indicates a copy-paste bug somewhere.
	type WithLabels = { subtype_id: string; subtype_label: string };
	const byLabel = new Map<string, string>();
	for (const e of entries as WithLabels[]) {
		const prev = byLabel.get(e.subtype_id);
		if (prev && prev !== e.subtype_label) {
			const msg = `[hlcl] subtype_id="${e.subtype_id}" has conflicting labels (${JSON.stringify(prev)} vs ${JSON.stringify(e.subtype_label)}); using the first`;
			if (logger) logger.warn(msg);
			else console.warn(msg);
		} else if (!prev) {
			byLabel.set(e.subtype_id, e.subtype_label);
		}
	}

	const banner =
		`// AUTO-GENERATED by vite/plugins/hlcl-build-assets.ts.\n` +
		`// DO NOT EDIT — your changes will be overwritten on the next dev save\n` +
		`// or production build. The source of truth is each\n` +
		`// hlcl/vendors/<mfg>/<family>/catalog.json file; the Vite plugin\n` +
		`// scans for them, validates against \`familyCatalogEntrySchema\`, and\n` +
		`// regenerates this module.\n`;

	const body =
		`import type { FamilyCatalogEntry } from '../schema';\n\n` +
		`export const CATALOG_ENTRIES: readonly FamilyCatalogEntry[] = ${JSON.stringify(
			entries,
			null,
			2
		)} as const;\n`;

	await mkdir(dirname(CATALOG_OUT), { recursive: true });
	await writeFile(CATALOG_OUT, banner + '\n' + body, 'utf8');
	return { entries: entries as FamilyCatalogEntryLike[] };
}

/**
 * Scan `hlcl/presets/*.json`, validate each file against
 * `presetFileSchema` (loaded via the schema module), and emit a typed
 * TypeScript module at `src/lib/_generated/presets.ts`. Preset files
 * are the source of truth for the configurator's "Presets" tab; each
 * one contains a fully-formed `BuildConfig` plus card metadata
 * (title, tagline, description, bullets).
 *
 * Validation errors fail the build loudly: a typo in a preset.json
 * file should surface immediately in the dev terminal, not as a
 * confusing runtime error in the Presets tab.
 *
 * Emits an empty PRESET_FILES array (still a valid TS module) when
 * `hlcl/presets/` is absent — keeps `npm run dev` working on a
 * partial checkout.
 */
async function emitPresetsModule(
	schemaMod: SchemaModule,
	logger?: ViteDevServer['config']['logger']
): Promise<{ entries: PresetFileLike[] }> {
	const presetsExists = await stat(PRESETS_DIR)
		.then((s) => s.isDirectory())
		.catch(() => false);

	const matches = presetsExists
		? await glob(['*.json'], { cwd: PRESETS_DIR, onlyFiles: true, dot: false })
		: [];
	matches.sort();

	const entries: unknown[] = [];
	const errors: string[] = [];
	const seenIds = new Map<string, string>(); // id → first-seen filename
	for (const rel of matches) {
		const abs = join(PRESETS_DIR, rel);
		let raw: unknown;
		try {
			raw = JSON.parse(await readFile(abs, 'utf8'));
		} catch (err) {
			const msg = err instanceof Error ? err.message : String(err);
			errors.push(`presets/${rel}: invalid JSON — ${msg}`);
			continue;
		}
		const result = schemaMod.parsePresetFile(raw);
		if (!result.ok || !result.value) {
			for (const e of result.errors ?? []) errors.push(`presets/${rel}: ${e}`);
			continue;
		}
		const value = result.value as PresetFileLike;
		const prev = seenIds.get(value.id);
		if (prev) {
			errors.push(`presets/${rel}: duplicate id "${value.id}" (first seen in presets/${prev})`);
			continue;
		}
		seenIds.set(value.id, rel);
		entries.push(value);
	}

	if (errors.length > 0) {
		const summary = errors.map((e) => `  • ${e}`).join('\n');
		const msg = `[hlcl] preset file validation failed:\n${summary}`;
		if (logger) logger.error(msg);
		else console.error(msg);
		throw new Error(`${errors.length} preset file(s) failed validation`);
	}

	// Stable ordering: sort_order asc, then id asc as a tiebreaker. The
	// PresetsTab renders cards in this order top-to-bottom-left-to-right.
	type Sortable = { sort_order: number; id: string };
	(entries as Sortable[]).sort((a, b) => {
		if (a.sort_order !== b.sort_order) return a.sort_order - b.sort_order;
		return a.id.localeCompare(b.id);
	});

	const banner =
		`// AUTO-GENERATED by vite/plugins/hlcl-build-assets.ts.\n` +
		`// DO NOT EDIT — your changes will be overwritten on the next dev save\n` +
		`// or production build. The source of truth is each\n` +
		`// hlcl/presets/<id>.json file; the Vite plugin scans for them,\n` +
		`// validates against \`presetFileSchema\`, and regenerates this module.\n`;

	const body =
		`import type { PresetFile } from '../schema';\n\n` +
		`export const PRESET_FILES: readonly PresetFile[] = ${JSON.stringify(
			entries,
			null,
			2
		)} as const;\n`;

	await mkdir(dirname(PRESETS_OUT), { recursive: true });
	await writeFile(PRESETS_OUT, banner + '\n' + body, 'utf8');
	return { entries: entries as PresetFileLike[] };
}

/**
 * Build the per-family `options` and `overrides` dicts for a catalog entry,
 * used to populate `factory-defaults.json`'s `families` map. Mirrors the
 * runtime population logic in `src/lib/state.svelte.ts::defaultFamilyConfig`,
 * but produces snake_case keys (Python-side consumers are snake_case-only).
 *
 * The "common" options that every family inherits from `libraries.ts`
 * (`enabled_densities`, `sizes`, `override_pad_radius`) live in the runtime
 * UI layer rather than in catalog.json. To keep `factory-defaults.json`
 * faithful to "what a user would see if they clicked Factory defaults",
 * we materialise those common options here too.
 */
function buildFactoryFamilies(
	entries: FamilyCatalogEntryLike[]
): Record<
	string,
	{ enabled: boolean; options: Record<string, unknown>; overrides: Record<string, boolean> }
> {
	const out: Record<
		string,
		{ enabled: boolean; options: Record<string, unknown>; overrides: Record<string, boolean> }
	> = {};
	for (const entry of entries) {
		const options: Record<string, unknown> = {};
		const overrides: Record<string, boolean> = {};

		// Common options (must stay in sync with libraries.ts::commonOptions).
		options['enabled_densities'] = ['L', 'N', 'M'];
		overrides['enabled_densities'] = false;
		options['sizes'] = [...entry.available_sizes];
		overrides['sizes'] = false;
		options['override_pad_radius'] = 25;
		overrides['override_pad_radius'] = false;

		// Catalog-specific options.
		for (const opt of entry.options ?? []) {
			const c = opt.control;
			switch (c.kind) {
				case 'toggle':
					options[opt.id] = c.default_value;
					break;
				case 'select':
					options[opt.id] = c.default_value;
					break;
				case 'multiselect':
					options[opt.id] = [...c.default_value];
					break;
				case 'number':
					options[opt.id] = c.default_value;
					break;
				case 'text':
					options[opt.id] = c.default_value;
					break;
			}
			if (opt.overrides_global) overrides[opt.id] = false;
		}

		// Every catalog-listed family is enabled by default — factory-defaults
		// matches the "build everything" semantics of the legacy `make all`
		// invocation, so a fresh CLI checkout still produces the full library.
		out[entry.id] = { enabled: true, options, overrides };
	}
	return out;
}

/**
 * Emit `hlcl/factory-defaults.json` — the canonical fallback config used by
 * `python hlcl/build.py` when no `--config` flag is given. Combines the
 * Zod-defined `defaultBuildConfig()` (settings, artifacts) with the
 * catalog-derived family map (every discovered family enabled).
 */
async function emitFactoryDefaults(
	schemaMod: SchemaModule,
	entries: FamilyCatalogEntryLike[]
): Promise<void> {
	const baseline = schemaMod.defaultBuildConfig();
	const families = buildFactoryFamilies(entries);
	const doc = {
		schema_version: baseline.schema_version,
		families,
		settings: baseline.settings,
		artifacts: baseline.artifacts,
		crosslinks: baseline.crosslinks
	};
	await mkdir(dirname(FACTORY_DEFAULTS_OUT), { recursive: true });
	await writeFile(FACTORY_DEFAULTS_OUT, JSON.stringify(doc, null, 2) + '\n', 'utf8');
}

/**
 * Coalesce rapid file-system events (npm install, batch saves) into a single
 * regen call. Idle for `quietMs` after the last event before re-running the
 * generator.
 */
function debounceAsync(fn: () => Promise<void>, quietMs = 200): () => void {
	let pending: NodeJS.Timeout | null = null;
	let running = Promise.resolve();
	return () => {
		if (pending) clearTimeout(pending);
		pending = setTimeout(() => {
			pending = null;
			running = running.then(fn).catch(() => {
				/* errors are surfaced via the plugin's logger; don't crash dev */
			});
		}, quietMs);
	};
}

/**
 * Standalone regeneration entry point. Invoked both from the Vite plugin
 * lifecycle hooks below AND from `vite/scripts/regen.ts` (called by the
 * `prepare` and `precheck` npm scripts so type-checking on a fresh clone
 * doesn't race the file emission).
 *
 * Caller-friendly signature: pass a reason string for log messages, and
 * optionally a Vite logger so emitted info/error lines route through the
 * same channel as the dev server. Without a logger we fall back to
 * `console`.
 */
export async function regenerateBuildAssets(
	reason: string,
	logger?: ViteDevServer['config']['logger']
): Promise<void> {
	const t0 = Date.now();
	try {
		const schemaMod = await loadSchemaModule();
		// Generate in two phases: first emit the catalog + schema sidecar +
		// factory-defaults (because the tarball needs factory-defaults.json
		// to already exist on disk to be packed), then emit the tarball.
		await emitSchemaSidecar(schemaMod);
		const catalogStats = await emitCatalogModule(schemaMod, logger);
		await emitFactoryDefaults(schemaMod, catalogStats.entries);
		const presetStats = await emitPresetsModule(schemaMod, logger);
		const tarballStats = await emitTarball();

		const dt = Date.now() - t0;
		const sizeMb = (tarballStats.bytes / 1024 / 1024).toFixed(2);
		const tarballSize = await stat(TARBALL_OUT)
			.then((s) => `${(s.size / 1024 / 1024).toFixed(2)} MiB gz`)
			.catch(() => '?');
		const msg = `[hlcl] regenerated build assets (${reason}) in ${dt} ms — schema + factory-defaults + ${tarballStats.files} tarball entries (${sizeMb} MiB raw → ${tarballSize}) + ${catalogStats.entries.length} catalog entries + ${presetStats.entries.length} presets`;
		if (logger) logger.info(msg);
		else console.log(msg);
	} catch (err) {
		const msg = err instanceof Error ? (err.stack ?? err.message) : String(err);
		if (logger) logger.error(`[hlcl] build-asset generation failed: ${msg}`);
		else console.error(`[hlcl] build-asset generation failed: ${msg}`);
		throw err;
	}
}

export function hlclBuildAssets(): Plugin {
	let regenerating = Promise.resolve();
	let logger: ViteDevServer['config']['logger'] | undefined;

	async function regenerate(reason: string): Promise<void> {
		await regenerateBuildAssets(reason, logger);
	}

	const triggerRegen = debounceAsync(() => regenerate('source changed'));

	return {
		name: 'hlcl-build-assets',
		// Run before SvelteKit's adapter copies `static/` into the production
		// output so the freshly-emitted files are picked up.
		enforce: 'pre',

		async buildStart() {
			regenerating = regenerate('build start');
			await regenerating;
		},

		async configureServer(server) {
			logger = server.config.logger;
			// AWAIT the first regen synchronously: Vite doesn't start serving
			// modules until every plugin's `configureServer` resolves, and
			// `src/lib/libraries.ts` imports the freshly-generated
			// `_generated/catalog.ts`. If we don't await here, the very first
			// HTTP request can race the regen on a fresh clone and 500.
			try {
				await regenerate('dev server start');
			} catch {
				// regenerate() already routed the error through `logger.error`;
				// don't crash the dev server — the user can fix the file and
				// the watcher below will pick up the save.
			}

			// Watch the source tree + the schema definition so saves on either
			// side roll forward into the asset trio. Also watch
			// docs/standards/ so edits to the LaTeX / Markdown templates
			// rebuild the tarball -- the in-browser standards target reads
			// them out of /hlcl/standards/ inside the unpacked tree.
			server.watcher.add(HLCL_SRC);
			server.watcher.add(SCHEMA_TS);
			server.watcher.add(DOCS_STANDARDS_DIR);
			server.watcher.on('all', (_event, file) => {
				const r = relative(PROJECT_ROOT, file);
				const isInHlcl = r.startsWith(`${HLCL_REL}${sep}`);
				const isInDocsStandards = r.startsWith(`${DOCS_STANDARDS_REL}${sep}`);
				if (r === relative(PROJECT_ROOT, SCHEMA_TS) || isInHlcl || isInDocsStandards) {
					// Skip events on the generated artifacts themselves to avoid
					// an infinite regeneration loop.
					if (r.endsWith('build-config.schema.json')) return;
					if (r.endsWith('factory-defaults.json')) return;
					if (r.endsWith('hlcl-build-inputs.tgz')) return;
					triggerRegen();
				}
			});
		}
	};
}
