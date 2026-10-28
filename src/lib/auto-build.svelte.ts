/**
 * Background builds for the configurator.
 *
 * Every configuration change schedules a rebuild once edits settle for
 * `DEBOUNCE_MS`. Builds run in the Pyodide worker, so the page stays
 * responsive. One build runs at a time; changes made during a build queue a
 * single follow-up build of the latest configuration. Outputs and banner
 * stats always describe `builtConfig`, which can trail the live config
 * while a rebuild is due. A configuration that failed is not retried
 * automatically until it changes (or the user clicks Build now).
 */
import { consoleLog } from './console.svelte';
import {
	cleanBuild,
	computeBuildStats,
	listBuildOutputs,
	runBuild,
	type BuildOutputFile
} from './hlcl-runner';
import type { BuildConfig } from './schema';
import { appState, configHash } from './state.svelte';

const DEBOUNCE_MS = 800;

class AutoBuild {
	/** Artifacts of the last completed build. */
	outputs = $state<BuildOutputFile[]>([]);
	builtConfig = $state.raw<BuildConfig | null>(null);
	builtHash = $state<string | null>(null);
	/** Hash of the build in progress, or null when idle. */
	buildingHash = $state<string | null>(null);
	/** Hash waiting to build (debouncing or behind the running build). */
	queuedHash = $state<string | null>(null);
	error = $state<string | null>(null);
	failedHash = $state<string | null>(null);
	/** Increments after every completed build so views can reload. */
	revision = $state(0);
	lastSeconds = $state<number | null>(null);

	#queued: BuildConfig | null = null;
	#due = false;
	#timer: ReturnType<typeof setTimeout> | undefined;

	get running(): boolean {
		return this.buildingHash !== null;
	}

	/** True when the last completed build matches `config` and nothing is pending. */
	isCurrent(config: BuildConfig): boolean {
		return !this.running && this.queuedHash === null && this.builtHash === configHash(config);
	}

	/** Schedule a rebuild of `config` once edits settle. */
	request(config: BuildConfig, delay = DEBOUNCE_MS): void {
		const hash = configHash(config);
		if (hash === (this.buildingHash ?? this.builtHash) || hash === this.failedHash) {
			this.#cancelQueued();
			return;
		}
		this.#queued = config;
		this.queuedHash = hash;
		this.#due = false;
		clearTimeout(this.#timer);
		this.#timer = setTimeout(() => {
			this.#due = true;
			void this.#pump();
		}, delay);
	}

	/** Build right away: manual mode, or retrying a failed configuration. */
	buildNow(config: BuildConfig): void {
		this.failedHash = null;
		this.request(config, 0);
	}

	#cancelQueued(): void {
		clearTimeout(this.#timer);
		this.#queued = null;
		this.queuedHash = null;
		this.#due = false;
	}

	async #pump(): Promise<void> {
		if (this.running || !this.#queued || !this.#due) return;
		const config = this.#queued;
		const hash = this.queuedHash as string;
		this.#cancelQueued();
		this.buildingHash = hash;
		this.error = null;
		const started = performance.now();
		try {
			let outputs: BuildOutputFile[] = [];
			let stats = { components: 0, unique_footprints: 0 };
			if (Object.values(config.families).some((f) => f.enabled)) {
				await cleanBuild();
				await runBuild(config);
				outputs = await listBuildOutputs();
				stats = await computeBuildStats();
			}
			this.outputs = outputs;
			this.builtConfig = config;
			this.builtHash = hash;
			this.failedHash = null;
			this.lastSeconds = (performance.now() - started) / 1000;
			this.revision++;
			appState.setBuildStats(stats, config);
			consoleLog.system(
				`Build finished in ${this.lastSeconds.toFixed(1)}s: ${outputs.length} artifacts, ` +
					`${stats.components.toLocaleString()} components, ` +
					`${stats.unique_footprints.toLocaleString()} unique footprints.`
			);
		} catch (err) {
			this.error = err instanceof Error ? err.message : String(err);
			this.failedHash = hash;
			consoleLog.error(`Build failed: ${this.error}`);
		} finally {
			this.buildingHash = null;
			// A change that settled while this build ran starts immediately.
			void this.#pump();
		}
	}
}

export const autoBuild = new AutoBuild();
