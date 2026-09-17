import assert from 'node:assert/strict';
import { test } from 'node:test';
import { validateRelease } from './release';

function fixture(development = true) {
	const version = development ? '0.2.0-dev' : '0.2.0';
	return {
		pkg: { version },
		lock: { version, packages: { '': { version } } },
		history: [
			{
				version: '0.2.0',
				status: development ? 'unreleased' : 'released',
				releasedOn: development ? null : '2026-09-17',
				changes: ['Correct ERA part numbers.']
			},
			{ version: '0.1.0', status: 'released', releasedOn: null, changes: ['Original website.'] }
		]
	};
}

test('development builds validate but cannot be promoted by a tag or stable flag', () => {
	const { pkg, lock, history } = fixture();
	assert.equal(validateRelease(pkg, lock, history).version, '0.2.0-dev');
	assert.throws(() => validateRelease(pkg, lock, history, { stable: true }), /stable version/);
	assert.throws(() => validateRelease(pkg, lock, history, { tag: 'v0.2.0-dev' }), /stable version/);
	assert.throws(() => validateRelease(pkg, lock, history, { tag: 'v0.2.0' }), /stable version/);
});

test('production requires the exact version tag', () => {
	const { pkg, lock, history } = fixture(false);
	assert.equal(validateRelease(pkg, lock, history, { tag: 'v0.2.0' }).version, '0.2.0');
	assert.throws(() => validateRelease(pkg, lock, history, { tag: 'v0.3.0' }), /Release tag/);
});

test('both lockfile versions must match', () => {
	const { pkg, lock, history } = fixture();
	lock.packages[''].version = '0.1.0';
	assert.throws(() => validateRelease(pkg, lock, history), /versions must match/);
	lock.packages[''].version = pkg.version;
	lock.version = '0.1.0';
	assert.throws(() => validateRelease(pkg, lock, history), /versions must match/);
});

test('release preparation requires a matching entry, released status, and valid date', () => {
	const { pkg, lock, history } = fixture(false);
	history[0].version = '0.3.0';
	assert.throws(() => validateRelease(pkg, lock, history), /newest history entry/);
	history[0].version = '0.2.0';
	history[0].status = 'unreleased';
	assert.throws(() => validateRelease(pkg, lock, history), /stable builds must be released/);
	history[0].status = 'released';
	history[0].releasedOn = null;
	assert.throws(() => validateRelease(pkg, lock, history), /needs a release date/);
	history[0].releasedOn = '2026-02-30';
	assert.throws(() => validateRelease(pkg, lock, history));
});

test('history cannot contain duplicate versions or past unreleased entries', () => {
	const { pkg, lock, history } = fixture();
	history[1].version = '0.2.0';
	history[1].releasedOn = '2026-09-16';
	assert.throws(() => validateRelease(pkg, lock, history), /unique and newest first/);
	history[1].version = '0.1.0';
	history[1].status = 'unreleased';
	assert.throws(() => validateRelease(pkg, lock, history), /Only the newest/);
});
