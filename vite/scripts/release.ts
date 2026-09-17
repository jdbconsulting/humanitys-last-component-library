import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';
import { z } from 'zod';

const stableVersion = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;
const packageSchema = z.object({ version: z.string() });
const historySchema = z
	.array(
		z.object({
			version: z.string().regex(stableVersion),
			status: z.enum(['unreleased', 'released']),
			releasedOn: z.iso.date().nullable(),
			changes: z.array(z.string().trim().min(1)).min(1)
		})
	)
	.min(1);

export function validateRelease(
	packageData: unknown,
	lockData: unknown,
	historyData: unknown,
	options: { stable?: boolean; tag?: string } = {}
) {
	const { version } = packageSchema.parse(packageData);
	const lock = packageSchema.extend({ packages: z.object({ '': packageSchema }) }).parse(lockData);
	const history = historySchema.parse(historyData);
	const current = history[0];
	const development = version.endsWith('-dev');
	const baseVersion = development ? version.slice(0, -4) : version;
	const ensure = (condition: boolean, message: string) => {
		if (!condition) throw new Error(message);
	};

	ensure(stableVersion.test(baseVersion), 'Use X.Y.Z or X.Y.Z-dev for the website version.');
	ensure(
		lock.version === version && lock.packages[''].version === version,
		'package.json and package-lock.json versions must match.'
	);
	ensure(
		current.version === baseVersion,
		'The newest history entry must match the website version.'
	);
	ensure(
		current.status === (development ? 'unreleased' : 'released'),
		'Development builds must be unreleased; stable builds must be released in the history.'
	);
	for (const [index, release] of history.entries()) {
		ensure(
			index === 0 || release.status === 'released',
			'Only the newest release may be unreleased.'
		);
		ensure(
			release.status !== 'unreleased' || release.releasedOn === null,
			'Unreleased versions must not have a release date.'
		);
		ensure(
			release.status !== 'released' || release.releasedOn !== null || release.version === '0.1.0',
			`Released version ${release.version} needs a release date (only the original 0.1.0 is undated).`
		);
		if (index > 0) {
			const previous = history[index - 1].version.split('.').map(Number);
			const parts = release.version.split('.').map(Number);
			const difference = previous.map((part, i) => part - parts[i]).find((part) => part !== 0);
			ensure(
				difference !== undefined && difference > 0,
				'History versions must be unique and newest first.'
			);
		}
	}
	if (options.stable || options.tag !== undefined) {
		ensure(!development, 'Production requires a stable version; development builds cannot deploy.');
	}
	if (options.tag !== undefined) {
		ensure(options.tag === `v${version}`, `Release tag must be v${version}.`);
	}
	return { version, current };
}

async function main() {
	const { values } = parseArgs({
		options: {
			stable: { type: 'boolean' },
			tag: { type: 'string' },
			notes: { type: 'string' }
		}
	});
	const root = new URL('../../', import.meta.url);
	const readJson = async (path: string) => JSON.parse(await readFile(new URL(path, root), 'utf8'));
	const [pkg, lock, history] = await Promise.all([
		readJson('package.json'),
		readJson('package-lock.json'),
		readJson('src/lib/release-history.json')
	]);
	const { version, current } = validateRelease(pkg, lock, history, values);
	if (values.notes) {
		await writeFile(
			values.notes,
			`# Website v${version}\n\n${current.releasedOn ?? 'Unreleased'}\n\n` +
				current.changes.map((change) => `- ${change}\n`).join('')
		);
	}
	console.log(`Website v${version}: release metadata validated.`);
}

if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) {
	await main();
}
