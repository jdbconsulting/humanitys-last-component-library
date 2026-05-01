"""
IPC-7351B chip-component land pattern math.

Direct port of ``house/HouseLibGenerator/IpcRules.cs`` and
``PadCalculator.cs``. See those files (and the reference PDF at
``references/ipc-7351b-*``) for the derivations and policy rationale.

All inputs and outputs are in millimetres. All component dimensions
are nominal-only (zero-tolerance per repo policy), so the C component-
tolerance terms drop out and the RMS reduces to ``sqrt(F^2 + P^2)``.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt


# ----- Tolerances, fixed by IPC-7351B §3.1.4 SOIC worked example -----

#: Fabrication tolerance F, mm.
FABRICATION_TOLERANCE_MM = 0.10

#: Placement tolerance P, mm.
PLACEMENT_TOLERANCE_MM = 0.05


# ----- Per-density rule rows ----------------------------------------


@dataclass(frozen=True)
class IpcChipRule:
    """Per-density IPC rule set for chip components.

    ``toe_jt``  -- Toe land protrusion goal J_T (mm).
    ``heel_jh`` -- Heel land protrusion goal J_H (mm); always 0 for chips.
    ``side_js`` -- Side land protrusion goal J_S (mm); can be negative.
    ``round_off_mm`` -- Round-off granularity per the table footer.
    ``courtyard_excess_mm`` -- Courtyard excess (we don't draw a
        courtyard, but kept here for completeness)."""

    toe_jt: float
    heel_jh: float
    side_js: float
    round_off_mm: float
    courtyard_excess_mm: float


def select_rule(body_length_mm: float, body_width_mm: float, density: str) -> IpcChipRule:
    """Pick which J/round-off table applies to a given chip body.

    The 1608-metric (0603-imperial) crossover sits on body length (the
    long axis along which the toe extends): metric 1608 itself uses
    Table 3-5; anything smaller uses Table 3-6.
    """
    is_large_body = body_length_mm >= 1.6 - 0.001
    return _table_3_5(density) if is_large_body else _table_3_6(density)


def _table_3_5(density: str) -> IpcChipRule:
    """Rectangular chip components >= 1608 metric (>= 0603 imperial)."""
    return _rule_for(
        density,
        most=    IpcChipRule(0.55, 0.0,  0.05, 0.05, 0.5),
        nominal= IpcChipRule(0.35, 0.0,  0.0,  0.05, 0.25),
        least=   IpcChipRule(0.15, 0.0, -0.05, 0.05, 0.1),
    )


def _table_3_6(density: str) -> IpcChipRule:
    """Rectangular chip components < 1608 metric (< 0603 imperial)."""
    return _rule_for(
        density,
        most=    IpcChipRule(0.30, 0.0,  0.05, 0.02, 0.2),
        nominal= IpcChipRule(0.20, 0.0,  0.0,  0.02, 0.15),
        least=   IpcChipRule(0.10, 0.0, -0.05, 0.02, 0.1),
    )


def _rule_for(density: str, *, most: IpcChipRule, nominal: IpcChipRule, least: IpcChipRule) -> IpcChipRule:
    if density == "M":
        return most
    if density == "N":
        return nominal
    if density == "L":
        return least
    raise ValueError(f"unknown density {density!r}; expected L/N/M")


# ----- Pad geometry result ------------------------------------------


@dataclass(frozen=True)
class IpcChipPad:
    """IPC pad geometry result for a two-terminal chip. All in mm.

    (Z, G, X) are the canonical IPC-7351B outputs; the per-pad fields
    are derived. Names use "along-terminal" / "across-terminal"
    rather than X/Y to keep the IPC-vs-CAD axis mapping unambiguous
    (see module docstring for the convention).
    """

    z_mm: float
    g_mm: float
    x_mm: float
    pad_center_spacing_mm: float
    pad_length_along_terminal_mm: float
    pad_width_across_terminal_mm: float


# ----- Land pattern math --------------------------------------------


def compute_pad(
    body_length_mm: float,
    body_width_mm: float,
    terminal_length_mm: float,
    rule: IpcChipRule,
) -> IpcChipPad:
    """Apply IPC-7351B §3.1.4 equations to derive (Z, G, X) plus per-
    pad CAD geometry. With repo's 0%-tolerance policy:

        S_max = L - 2*T
        Z_max = L + 2*J_T + sqrt(F^2 + P^2)
        G_min = S_max - 2*J_H - sqrt(F^2 + P^2)
        X_max = W + 2*J_S + sqrt(F^2 + P^2)

    Each value is then rounded to the table's quantisation (0.05 mm
    for >= 1608 metric bodies, 0.02 mm for smaller). Rounding mode is
    half-away-from-zero to match Altium's IPC LP Calculator.
    """
    rms = sqrt(FABRICATION_TOLERANCE_MM ** 2 + PLACEMENT_TOLERANCE_MM ** 2)

    s_max = body_length_mm - 2.0 * terminal_length_mm
    z_max = body_length_mm + 2.0 * rule.toe_jt + rms
    g_min = s_max - 2.0 * rule.heel_jh - rms
    x_max = body_width_mm + 2.0 * rule.side_js + rms

    z_r = _round_to_step(z_max, rule.round_off_mm)
    g_r = _round_to_step(g_min, rule.round_off_mm)
    x_r = _round_to_step(x_max, rule.round_off_mm)

    return IpcChipPad(
        z_mm=z_r,
        g_mm=g_r,
        x_mm=x_r,
        pad_center_spacing_mm=(z_r + g_r) / 2.0,
        pad_length_along_terminal_mm=(z_r - g_r) / 2.0,
        pad_width_across_terminal_mm=x_r,
    )


def _round_to_step(value: float, step_mm: float) -> float:
    """Round ``value`` to the nearest multiple of ``step_mm`` with
    half-away-from-zero at the midpoint -- matches Altium's IPC LP
    Calculator and .NET's ``Math.Round(.., MidpointRounding.AwayFromZero)``,
    not Python's banker's-rounding default. Re-quantise to 4 decimal
    places so the .PcbLib doesn't accumulate IEEE-754 noise."""
    if step_mm <= 0.0:
        return value
    quotient = value / step_mm
    if quotient >= 0:
        rounded_q = int(quotient + 0.5)
    else:
        rounded_q = -int(-quotient + 0.5)
    rounded = rounded_q * step_mm
    return round(rounded, 4)
