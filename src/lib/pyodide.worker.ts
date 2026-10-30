/// <reference lib="webworker" />
// Pyodide runs in this dedicated worker so builds never block the page.
// The main thread talks to it through `pyodide.ts`; requests run strictly
// one at a time, because Python code awaiting inside one request (the build
// yields with `asyncio.sleep(0)`) must not interleave with another.

const PYODIDE_VERSION = '0.28.0';
const PYODIDE_BASE = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

export type WorkerRequest =
	| { id: number; op: 'runPython'; code: string }
	| { id: number; op: 'loadPackage'; names: string[] }
	| { id: number; op: 'writeFile'; path: string; data: Uint8Array | string }
	| { id: number; op: 'readFile'; path: string };

export type WorkerMessage =
	| { type: 'log'; stream: 'system' | 'stdout' | 'stderr'; text: string }
	| { type: 'result'; id: number; ok: true; result: unknown }
	| { type: 'result'; id: number; ok: false; error: string };

interface Runtime {
	version: string;
	runPythonAsync(code: string): Promise<unknown>;
	loadPackage(names: string[]): Promise<void>;
	setStdout(opts: { batched: (s: string) => void }): void;
	setStderr(opts: { batched: (s: string) => void }): void;
	FS: {
		mkdirTree(path: string): void;
		writeFile(path: string, data: Uint8Array | string): void;
		readFile(path: string): Uint8Array;
	};
}

const scope = self as unknown as DedicatedWorkerGlobalScope;
const post = (message: WorkerMessage, transfer: Transferable[] = []) =>
	scope.postMessage(message, transfer);

let runtime: Promise<Runtime> | null = null;

function getRuntime(): Promise<Runtime> {
	runtime ??= (async () => {
		post({ type: 'log', stream: 'system', text: `Loading Pyodide ${PYODIDE_VERSION} from CDN…` });
		const { loadPyodide } = await import(/* @vite-ignore */ `${PYODIDE_BASE}pyodide.mjs`);
		const py = (await loadPyodide({ indexURL: PYODIDE_BASE })) as Runtime;
		py.setStdout({ batched: (text) => text && post({ type: 'log', stream: 'stdout', text }) });
		py.setStderr({ batched: (text) => text && post({ type: 'log', stream: 'stderr', text }) });
		post({ type: 'log', stream: 'system', text: `Pyodide ${py.version} ready.` });
		return py;
	})().catch((err) => {
		runtime = null;
		throw err;
	});
	return runtime;
}

async function handle(req: WorkerRequest): Promise<void> {
	try {
		const py = await getRuntime();
		switch (req.op) {
			case 'runPython': {
				const value = await py.runPythonAsync(req.code);
				post({ type: 'result', id: req.id, ok: true, result: value ?? null });
				break;
			}
			case 'loadPackage':
				await py.loadPackage(req.names);
				post({ type: 'result', id: req.id, ok: true, result: null });
				break;
			case 'writeFile':
				py.FS.mkdirTree(req.path.slice(0, req.path.lastIndexOf('/')) || '/');
				py.FS.writeFile(req.path, req.data);
				post({ type: 'result', id: req.id, ok: true, result: null });
				break;
			case 'readFile': {
				const bytes = py.FS.readFile(req.path);
				post({ type: 'result', id: req.id, ok: true, result: bytes }, [bytes.buffer]);
				break;
			}
		}
	} catch (err) {
		post({
			type: 'result',
			id: req.id,
			ok: false,
			error: err instanceof Error ? err.message : String(err)
		});
	}
}

let queue = Promise.resolve();
scope.onmessage = (event: MessageEvent<WorkerRequest>) => {
	queue = queue.then(() => handle(event.data));
};
