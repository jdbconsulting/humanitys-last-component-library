<svelte:head>
	<title>Component selection advice · Docs · HLCL</title>
</svelte:head>

<h1 class="text-3xl font-bold tracking-tight text-ink-900">Component selection advice</h1>

<div class="prose-docs mt-8 space-y-5 text-ink-700">
	<p>
		Start from the electrical job, then narrow by availability, package size, qualification needs,
		and the supply chain your team actually uses.
	</p>

	<h2 class="text-xl font-semibold text-ink-900">Resistors</h2>
	<ul class="list-disc space-y-2 pl-5">
		<li>
			Choose technology by the role in the circuit:
			<ul class="mt-2 list-disc space-y-1 pl-5">
				<li>
					<strong class="text-ink-900">Thick film:</strong> default for commodity pullups, dividers, biasing,
					LEDs, and low-cost general SMT use.
				</li>
				<li>
					<strong class="text-ink-900">Thin film:</strong> use for precision gain setting, filtering,
					references, low noise, and tighter temperature coefficient needs.
				</li>
				<li>
					<strong class="text-ink-900">Metal film:</strong> useful where stable precision, low noise,
					or through-hole/lead-based families are preferred.
				</li>
				<li>
					<strong class="text-ink-900">Current-sense:</strong> choose for low-value shunts; check power
					rating, Kelvin options, TCR, and pulse rating.
				</li>
				<li>
					<strong class="text-ink-900">Anti-sulfur:</strong> use for industrial, outdoor, automotive,
					or other sulfur/corrosion-prone environments.
				</li>
				<li>
					<strong class="text-ink-900">Surge/high-voltage:</strong> use for inputs, protection, discharge
					paths, mains-adjacent circuits, and high divider voltages.
				</li>
				<li>
					<strong class="text-ink-900">Wide-terminal/high-power:</strong> use when thermal spreading,
					board heat transfer, or power density matters.
				</li>
				<li>
					<strong class="text-ink-900">Automotive/high-reliability:</strong> use AEC-Q200 or qualified
					series when the environment, customer, or lifecycle requires it.
				</li>
			</ul>
		</li>
		<li>
			Keep the core generic set practical:
			<ul class="mt-2 list-disc space-y-1 pl-5">
				<li><strong class="text-ink-900">Panasonic:</strong> baseline mainstream anchor.</li>
				<li><strong class="text-ink-900">Yageo:</strong> broad commodity second source.</li>
				<li>
					<strong class="text-ink-900">Vishay:</strong> industrial, automotive, precision, and higher-reliability
					coverage.
				</li>
				<li>
					<strong class="text-ink-900">KOA Speer:</strong> precision, anti-sulfur, current-sense, surge,
					high-voltage, and wide-terminal options.
				</li>
				<li>
					<strong class="text-ink-900">Stackpole:</strong> common North American thick-film and thin-film
					second source.
				</li>
				<li>
					<strong class="text-ink-900">Bourns:</strong> current-sense, surge, sulfur-resistant, and automotive
					variants.
				</li>
				<li>
					<strong class="text-ink-900">ROHM:</strong> compact, automotive, and higher-power mainstream
					coverage.
				</li>
			</ul>
		</li>
		<li>
			Add specialist or volume vendors only when they solve a real sourcing or performance need:
			<ul class="mt-2 list-disc space-y-1 pl-5">
				<li>
					<strong class="text-ink-900">Susumu:</strong> precision analog, instrumentation, and thin-film
					stability.
				</li>
				<li>
					<strong class="text-ink-900">Samsung Electro-Mechanics:</strong> optional high-volume Asian
					passive supply chain coverage.
				</li>
			</ul>
		</li>
	</ul>

	<h2 class="text-xl font-semibold text-ink-900">Capacitors</h2>
	<ul class="list-disc space-y-2 pl-5">
		<li>
			Choose the dielectric before the vendor:
			<ul class="mt-2 list-disc space-y-1 pl-5">
				<li>
					<strong class="text-ink-900">C0G/NP0:</strong> timing, filters, RF matching, precision analog,
					and other stability-sensitive circuits.
				</li>
				<li>
					<strong class="text-ink-900">X7R:</strong> default MLCC choice for general decoupling and moderate-value
					capacitance over temperature.
				</li>
				<li>
					<strong class="text-ink-900">X5R:</strong> compact local bypassing when the temperature range
					and tolerance stack are understood.
				</li>
			</ul>
		</li>
		<li>
			Do not select MLCCs by nominal capacitance alone:
			<ul class="mt-2 list-disc space-y-1 pl-5">
				<li>Derate voltage enough for the circuit, environment, and reliability target.</li>
				<li>
					Check DC-bias curves; small high-value MLCCs can lose a large fraction of effective
					capacitance.
				</li>
				<li>
					Treat package size as an electrical choice, not just a layout choice; 0402 and 0805 parts
					with the same nominal value may behave very differently.
				</li>
			</ul>
		</li>
		<li>
			Use package size intentionally:
			<ul class="mt-2 list-disc space-y-1 pl-5">
				<li>Smaller packages help dense local decoupling and low parasitics.</li>
				<li>Larger packages often improve voltage headroom, DC-bias behavior, and availability.</li>
				<li>
					Watch mechanical cracking risk on larger MLCCs, especially near board edges, connectors,
					or high-flex areas.
				</li>
			</ul>
		</li>
		<li>
			Leave MLCCs when another capacitor type fits better:
			<ul class="mt-2 list-disc space-y-1 pl-5">
				<li>
					<strong class="text-ink-900">Polymer:</strong> bulk output capacitance with low ESR.
				</li>
				<li>
					<strong class="text-ink-900">Tantalum:</strong> compact bulk capacitance when surge and derating
					rules are acceptable.
				</li>
				<li>
					<strong class="text-ink-900">Aluminum electrolytic:</strong> cost-effective bulk energy storage
					or high capacitance.
				</li>
				<li>
					<strong class="text-ink-900">Film:</strong> precision, low loss, AC, pulse, snubber, or safety-related
					applications.
				</li>
			</ul>
		</li>
	</ul>

	<h2 class="text-xl font-semibold text-ink-900">Inductors</h2>
	<ul class="list-disc space-y-2 pl-5">
		<li>
			Separate beads from energy-storage inductors:
			<ul class="mt-2 list-disc space-y-1 pl-5">
				<li>
					<strong class="text-ink-900">Ferrite beads:</strong> lossy EMI parts for isolating noise over
					a frequency range; not power inductors.
				</li>
				<li>
					<strong class="text-ink-900">Power inductors:</strong> switching-converter and filter parts
					where saturation, ripple current, DCR, and thermals drive selection.
				</li>
			</ul>
		</li>
		<li>
			Check the current ratings behind the headline number:
			<ul class="mt-2 list-disc space-y-1 pl-5">
				<li>Saturation current: where inductance falls below the useful limit.</li>
				<li>Temperature-rise current: where self-heating reaches the vendor's stated limit.</li>
				<li>DCR: lower DCR improves efficiency but usually costs size, price, or availability.</li>
				<li>
					Inductance tolerance and bias behavior: important for ripple, control-loop margin, and
					peak current.
				</li>
			</ul>
		</li>
		<li>
			Account for EMI and placement:
			<ul class="mt-2 list-disc space-y-1 pl-5">
				<li>Use shielded inductors near sensitive analog, RF, sensors, or high-gain circuitry.</li>
				<li>
					Consider unshielded parts only when field coupling, emissions, and layout are benign.
				</li>
				<li>Review audible-noise behavior when ceramic capacitors and power magnetics interact.</li>
			</ul>
		</li>
		<li>
			Prefer vendor-qualified regulator series when available:
			<ul class="mt-2 list-disc space-y-1 pl-5">
				<li>Start from regulator reference designs or design-tool recommendations.</li>
				<li>Use qualified series when loop stability, thermals, emissions, or noise are tight.</li>
				<li>
					Still verify saturation, DCR, package, temperature rise, and lifecycle availability.
				</li>
			</ul>
		</li>
	</ul>
</div>
