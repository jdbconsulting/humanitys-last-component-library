/**
 * Reactive console for streaming Python output, build progress, and tool messages.
 *
 * Held in a Svelte 5 class so any component can `import { consoleLog }` and bind to
 * `consoleLog.entries` reactively. Append-only; the UI ring-buffers as needed.
 */

export type ConsoleLevel = 'info' | 'warn' | 'error' | 'stdout' | 'stderr' | 'system';

export interface ConsoleEntry {
	id: number;
	timestamp: number;
	level: ConsoleLevel;
	text: string;
}

class ConsoleLog {
	#nextId = 1;
	entries = $state<ConsoleEntry[]>([]);
	maxEntries = 1000;

	push(level: ConsoleLevel, text: string): void {
		const lines = text.split('\n');
		for (const line of lines) {
			if (line.length === 0 && lines.length > 1) continue;
			this.entries.push({
				id: this.#nextId++,
				timestamp: Date.now(),
				level,
				text: line
			});
		}
		if (this.entries.length > this.maxEntries) {
			this.entries.splice(0, this.entries.length - this.maxEntries);
		}
	}

	info(text: string): void {
		this.push('info', text);
	}
	warn(text: string): void {
		this.push('warn', text);
	}
	error(text: string): void {
		this.push('error', text);
	}
	system(text: string): void {
		this.push('system', text);
	}
	stdout(text: string): void {
		this.push('stdout', text);
	}
	stderr(text: string): void {
		this.push('stderr', text);
	}

	clear(): void {
		this.entries = [];
	}
}

export const consoleLog = new ConsoleLog();
