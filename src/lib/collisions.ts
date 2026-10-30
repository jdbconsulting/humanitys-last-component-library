/**
 * Footprint-name collisions from the last build.
 *
 * The house merge (`hlcl/house/build_house_footprints.py`) records every
 * footprint name that more than one family emitted. Names only overlap
 * when families use generic IPC-7351B footprint names; vendor-specific
 * names (the default) never collide. Vendors are vendor keys, the same
 * ids `settings.house_footprints.priority` uses.
 */

export interface FootprintCollision {
	/** Full footprint name including the density letter, e.g. `RESC1608X45N`. */
	name: string;
	/** Vendor keys that emitted it, in the priority order the build used. */
	vendors: string[];
	/** True when every vendor's geometry for this name is identical. */
	sameGeometry: boolean;
}

export interface CollisionReport {
	collisions: FootprintCollision[];
	/** Vendor key -> catalog family id (they differ only for a few families). */
	familyIds: Record<string, string>;
}

/** One footprint root (density letters folded together) shared by several vendors. */
export interface SharedRoot {
	root: string;
	densities: string[];
	vendors: string[];
	sameGeometry: boolean;
}

/**
 * Colliding vendor keys in the order the merge applies them: ranked by
 * `priority`, then any unranked ones alphabetically (as the merge does).
 */
export function collidingVendors(report: CollisionReport, priority: readonly string[]): string[] {
	const colliding = [...new Set(report.collisions.flatMap((c) => c.vendors))];
	const ranked = priority.filter((key) => colliding.includes(key));
	const unranked = colliding.filter((key) => !priority.includes(key)).sort();
	return [...ranked, ...unranked];
}

/** Collisions grouped by root, sorted by root name. */
export function sharedRoots(report: CollisionReport): SharedRoot[] {
	const byRoot: Record<string, SharedRoot> = {};
	for (const c of report.collisions) {
		const root = c.name.slice(0, -1);
		const entry = (byRoot[root] ??= { root, densities: [], vendors: [], sameGeometry: true });
		entry.densities.push(c.name.slice(-1));
		for (const v of c.vendors) if (!entry.vendors.includes(v)) entry.vendors.push(v);
		entry.sameGeometry &&= c.sameGeometry;
	}
	for (const entry of Object.values(byRoot)) {
		entry.densities.sort((a, b) => 'LNM'.indexOf(a) - 'LNM'.indexOf(b));
	}
	return Object.values(byRoot).sort((a, b) => a.root.localeCompare(b.root));
}

/**
 * New priority list after reordering the colliding vendors: the reordered
 * vendors first, then every other entry in its previous order.
 */
export function withReordered(priority: readonly string[], reordered: readonly string[]): string[] {
	return [...reordered, ...priority.filter((key) => !reordered.includes(key))];
}
