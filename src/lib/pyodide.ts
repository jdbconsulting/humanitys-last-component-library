// Main-thread client for the Pyodide worker (`pyodide.worker.ts`).
//
// Pyodide loads from the official jsdelivr CDN inside a dedicated worker, so
// long builds never block the UI. Worker stdout/stderr stream into the app's
// reactive console. The worker is created lazily on first use and reused.

import { consoleLog } from './console.svelte';
import type { WorkerMessage, WorkerRequest } from './pyodide.worker';

type Pending = { resolve: (value: unknown) => void; reject: (err: Error) => void };

let worker: Worker | null = null;
let nextId = 1;
const pending = new Map<number, Pending>();

// Builds print hundreds of lines in bursts. Applying them to the console
// together (at most every LOG_FLUSH_MS) keeps that to one render per burst.
const LOG_FLUSH_MS = 100;
type LogMessage = Extract<WorkerMessage, { type: 'log' }>;
let logBuffer: LogMessage[] = [];
let logTimer: ReturnType<typeof setTimeout> | undefined;

function flushLogs(): void {
	logTimer = undefined;
	const batch = logBuffer;
	logBuffer = [];
	for (const msg of batch) consoleLog[msg.stream](msg.text);
}

function failAll(message: string): void {
	for (const p of pending.values()) p.reject(new Error(message));
	pending.clear();
}

function getWorker(): Worker {
	if (worker) return worker;
	if (typeof Worker === 'undefined') throw new Error('Pyodide requires a browser');
	const w = new Worker(new URL('./pyodide.worker.ts', import.meta.url), { type: 'module' });
	w.onmessage = (event: MessageEvent<WorkerMessage>) => {
		const msg = event.data;
		if (msg.type === 'log') {
			logBuffer.push(msg);
			logTimer ??= setTimeout(flushLogs, LOG_FLUSH_MS);
			return;
		}
		// Results flush pending logs first so output stays in order.
		if (logTimer !== undefined) {
			clearTimeout(logTimer);
			flushLogs();
		}
		const p = pending.get(msg.id);
		if (!p) return;
		pending.delete(msg.id);
		if (msg.ok) p.resolve(msg.result);
		else p.reject(new Error(msg.error));
	};
	w.onerror = (event) => {
		failAll(`Pyodide worker failed: ${event.message || 'unknown error'}`);
		w.terminate();
		if (worker === w) worker = null;
	};
	worker = w;
	return w;
}

/** A request without its id, keeping each op's own fields (distributive). */
type RequestBody = {
	[Op in WorkerRequest['op']]: Omit<Extract<WorkerRequest, { op: Op }>, 'id'>;
}[WorkerRequest['op']];

function call(payload: RequestBody, transfer: Transferable[] = []): Promise<unknown> {
	return new Promise((resolve, reject) => {
		const id = nextId++;
		pending.set(id, { resolve, reject });
		try {
			getWorker().postMessage({ ...payload, id }, transfer);
		} catch (err) {
			pending.delete(id);
			reject(err instanceof Error ? err : new Error(String(err)));
		}
	});
}

/** The Pyodide operations the HLCL runner needs, executed in the worker. */
export const pyodide = {
	/** Run Python; resolves to the last expression's value (strings stay strings). */
	runPython: (code: string) => call({ op: 'runPython', code }),
	loadPackage: async (names: string[]) => void (await call({ op: 'loadPackage', names })),
	/** Write a file into MEMFS, creating parent directories. */
	writeFile: async (path: string, data: Uint8Array | string) =>
		void (await call(
			{ op: 'writeFile', path, data },
			typeof data === 'string' ? [] : [data.buffer]
		)),
	readFile: async (path: string) => (await call({ op: 'readFile', path })) as Uint8Array
};

/** Terminate the worker so the next call starts a fresh interpreter. */
export function resetPyodide(): void {
	worker?.terminate();
	worker = null;
	failAll('Pyodide worker was reset');
}
