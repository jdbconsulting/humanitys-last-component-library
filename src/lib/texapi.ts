/**
 * Thin client for the Texapi LaTeX → PDF compilation service.
 * https://texapi.ovh/docs
 *
 * ⚠ The API key is embedded in the client bundle. This is acceptable for a
 * personal / internal tool but the key should be rotated if the app is ever
 * made publicly accessible.
 */

const BASE_URL = 'https://texapi.ovh';
const API_KEY = 'o33g7q4Kgtk2q616d77AVa9zbhBpMX2CpthLJXCfLGk';

export type TexapiCompiler = 'pdflatex' | 'xelatex' | 'lualatex';

export interface TexapiResponse {
	status: 'success' | 'error';
	errors: string[];
	resultPath: string | null;
	outputFiles: { type: string; content: string }[] | null;
}

/**
 * Compile a single LaTeX string.
 * Use for simple, single-file documents without external assets.
 */
export async function compileLaTeX(
	content: string,
	compiler: TexapiCompiler = 'pdflatex'
): Promise<TexapiResponse> {
	const res = await fetch(`${BASE_URL}/api/latex/compile`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			'X-API-KEY': API_KEY
		},
		body: JSON.stringify({ content, compiler })
	});
	if (!res.ok) throw new Error(`Texapi HTTP ${res.status}: ${res.statusText}`);
	return res.json() as Promise<TexapiResponse>;
}

/**
 * Compile a multi-file LaTeX project (assets, fonts, bibliographies, etc.).
 * Files are passed as name+content pairs and uploaded as a multipart form.
 */
export async function compileLaTeXFiles(
	files: { name: string; content: string | Blob }[],
	mainFile: string,
	compiler: TexapiCompiler = 'pdflatex'
): Promise<TexapiResponse> {
	const form = new FormData();
	for (const f of files) {
		const blob =
			f.content instanceof Blob ? f.content : new Blob([f.content], { type: 'text/plain' });
		form.append('files', blob, f.name);
	}
	const url = `${BASE_URL}/api/latex/compile/file?compiler=${compiler}&mainFile=${encodeURIComponent(mainFile)}`;
	const res = await fetch(url, {
		method: 'POST',
		headers: { 'X-API-KEY': API_KEY },
		body: form
	});
	if (!res.ok) throw new Error(`Texapi HTTP ${res.status}: ${res.statusText}`);
	return res.json() as Promise<TexapiResponse>;
}

/**
 * Download the compiled PDF by its `resultPath` key.
 * The file is only available for 10 minutes after compilation.
 */
export async function downloadPdf(resultPath: string): Promise<Blob> {
	// resultPath may be the full path segment returned by the API, e.g. "/api/latex/files/abc123"
	const url = resultPath.startsWith('http')
		? resultPath
		: `${BASE_URL}${resultPath.startsWith('/') ? '' : '/'}${resultPath}`;
	const res = await fetch(url, { headers: { 'X-API-KEY': API_KEY } });
	if (!res.ok) throw new Error(`Texapi download HTTP ${res.status}: ${res.statusText}`);
	return res.blob();
}

/** Trigger a browser download of a Blob. */
export function saveBlobAs(blob: Blob, filename: string): void {
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = filename;
	document.body.appendChild(a);
	a.click();
	a.remove();
	URL.revokeObjectURL(url);
}
