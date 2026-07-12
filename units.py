from decimal import Decimal, getcontext
import re

getcontext().prec = 40


UNIT_DEFS = {
    # Length, base: m
    "m": {"dimension": "length", "to_base": Decimal("1")},
    "cm": {"dimension": "length", "to_base": Decimal("0.01")},
    "mm": {"dimension": "length", "to_base": Decimal("0.001")},
    "um": {"dimension": "length", "to_base": Decimal("1e-6")},
    "nm": {"dimension": "length", "to_base": Decimal("1e-9")},
    "ft": {"dimension": "length", "to_base": Decimal("0.3048")},
    "in": {"dimension": "length", "to_base": Decimal("0.0254")},

    # Mass, base: kg
    "kg": {"dimension": "mass", "to_base": Decimal("1")},
    "g": {"dimension": "mass", "to_base": Decimal("0.001")},
    "mg": {"dimension": "mass", "to_base": Decimal("1e-6")},
    "lb": {"dimension": "mass", "to_base": Decimal("0.45359237")},

    # Time, base: s
    "s": {"dimension": "time", "to_base": Decimal("1")},
    "ms": {"dimension": "time", "to_base": Decimal("0.001")},
    "us": {"dimension": "time", "to_base": Decimal("1e-6")},
    "ns": {"dimension": "time", "to_base": Decimal("1e-9")},

    # Energy, base: J
    "J": {"dimension": "energy", "to_base": Decimal("1")},
    "erg": {"dimension": "energy", "to_base": Decimal("1e-7")},
    "eV": {"dimension": "energy", "to_base": Decimal("1.602176634e-19")},
    "keV": {"dimension": "energy", "to_base": Decimal("1.602176634e-16")},
    "MeV": {"dimension": "energy", "to_base": Decimal("1.602176634e-13")},
    "GeV": {"dimension": "energy", "to_base": Decimal("1.602176634e-10")},

    # Force, base: N
    "N": {"dimension": "force", "to_base": Decimal("1")},
    "dyn": {"dimension": "force", "to_base": Decimal("1e-5")},
    "lbf": {"dimension": "force", "to_base": Decimal("4.4482216152605")},

    # Pressure, base: Pa
    "Pa": {"dimension": "pressure", "to_base": Decimal("1")},
    "bar": {"dimension": "pressure", "to_base": Decimal("1e5")},
    "atm": {"dimension": "pressure", "to_base": Decimal("101325")},
    "psi": {"dimension": "pressure", "to_base": Decimal("6894.757293168")},

    # Charge, base: C
    "C": {"dimension": "charge", "to_base": Decimal("1")},

    # Temperature, base: K
    "K": {"dimension": "temperature", "to_base": Decimal("1")},

    # Amount, base: mol
    "mol": {"dimension": "amount", "to_base": Decimal("1")},

    # Current, base: A
    "A": {"dimension": "current", "to_base": Decimal("1")},

    # Frequency, base: Hz
    "Hz": {"dimension": "frequency", "to_base": Decimal("1")},
    "kHz": {"dimension": "frequency", "to_base": Decimal("1e3")},
    "MHz": {"dimension": "frequency", "to_base": Decimal("1e6")},
    "GHz": {"dimension": "frequency", "to_base": Decimal("1e9")},
}


SYSTEM_DEFAULTS = {
    "mks": {
        "length": "m",
        "mass": "kg",
        "time": "s",
        "energy": "J",
        "force": "N",
        "pressure": "Pa",
        "charge": "C",
        "temperature": "K",
        "amount": "mol",
        "current": "A",
        "frequency": "Hz",
    },
    "cgs": {
        "length": "cm",
        "mass": "g",
        "time": "s",
        "energy": "erg",
        "force": "dyn",
        "pressure": "Pa",
        "charge": "C",
        "temperature": "K",
        "amount": "mol",
        "current": "A",
        "frequency": "Hz",
    },
    "imperial": {
        "length": "ft",
        "mass": "lb",
        "time": "s",
        "energy": "J",
        "force": "lbf",
        "pressure": "psi",
        "charge": "C",
        "temperature": "K",
        "amount": "mol",
        "current": "A",
        "frequency": "Hz",
    },
}


# Matches:
#   [J]
#   [s]^-1
#   [m]^3
#   [kg]^-1
#   [m]^3*[kg]^-1*[s]^-2
#
# Captures:
#   group 1: unit name, e.g. m, kg, s, J
#   group 2: exponent if present, e.g. 3, -1, -2
UNIT_FACTOR_RE = re.compile(r"\[([^\[\]]+)\](?:\^(-?\d+))?")


def parse_unit_expr(unit_expr: str) -> list[tuple[str, int]]:
    """
    Converts your JSON unit format into parsed unit factors.

    Examples:
      '[J]*[s]'                 -> [('J', 1), ('s', 1)]
      '[m]*[s]^-1'              -> [('m', 1), ('s', -1)]
      '[m]^3*[kg]^-1*[s]^-2'    -> [('m', 3), ('kg', -1), ('s', -2)]
      '[1]'                     -> []
    """
    unit_expr = unit_expr.strip()

    if not unit_expr or unit_expr == "[1]":
        return []

    parsed = []

    for match in UNIT_FACTOR_RE.finditer(unit_expr):
        unit = match.group(1).strip()
        exponent = int(match.group(2) or "1")

        if unit == "1":
            continue

        parsed.append((unit, exponent))

    return parsed


def format_unit_expr(units: list[tuple[str, int]]) -> str:
    """
    Converts parsed units back to your JSON/internal format.

    Examples:
      [('J', 1), ('s', 1)]              -> '[J]*[s]'
      [('m', 1), ('s', -1)]             -> '[m]*[s]^-1'
      [('m', 3), ('kg', -1), ('s', -2)] -> '[m]^3*[kg]^-1*[s]^-2'
    """
    if not units:
        return "[1]"

    parts = []

    for unit, exponent in units:
        if exponent == 1:
            parts.append(f"[{unit}]")
        else:
            parts.append(f"[{unit}]^{exponent}")

    return "*".join(parts)


def display_unit_expr(unit_expr: str) -> str:
    """
    Converts internal expression into display text.

    Examples:
      '[J]*[s]'                 -> 'J s'
      '[m]*[s]^-1'              -> 'm s^-1'
      '[m]^3*[kg]^-1*[s]^-2'    -> 'm^3 kg^-1 s^-2'
      '[1]'                     -> ''
    """
    parsed = parse_unit_expr(unit_expr)

    if not parsed:
        return ""

    parts = []

    for unit, exponent in parsed:
        if exponent == 1:
            parts.append(unit)
        else:
            parts.append(f"{unit}^{exponent}")

    return " ".join(parts)


def get_target_unit(source_unit: str, settings: dict) -> str:
    """
    Determines what unit source_unit should become based on:
      1. explicit override for its dimension
      2. selected system default
      3. fallback to original source_unit
    """
    if source_unit not in UNIT_DEFS:
        return source_unit

    dimension = UNIT_DEFS[source_unit]["dimension"]

    overrides = settings.get("overrides", {})
    if dimension in overrides:
        return overrides[dimension]

    system = settings.get("system", "mks")
    system_defaults = SYSTEM_DEFAULTS.get(system, SYSTEM_DEFAULTS["mks"])

    return system_defaults.get(dimension, source_unit)


def convert_value_and_unit(value_str: str, unit_expr: str, settings: dict) -> tuple[str, str]:
    """
    Converts a value/unit expression according to current unit settings.

    Example:
      value_str = '6.62607015e-34'
      unit_expr = '[J]*[s]'
      settings = {'system': 'mks', 'overrides': {'energy': 'eV'}}

      returns approximately:
      ('4.13566770e-15', '[eV]*[s]')

    Example:
      value_str = '299792458'
      unit_expr = '[m]*[s]^-1'
      settings = {'system': 'cgs', 'overrides': {}}

      returns approximately:
      ('2.99792458e10', '[cm]*[s]^-1')
    """
    value = Decimal(value_str)
    parsed = parse_unit_expr(unit_expr)

    total_factor = Decimal("1")
    new_units = []

    for source_unit, exponent in parsed:
        target_unit = get_target_unit(source_unit, settings)

        if source_unit not in UNIT_DEFS:
            new_units.append((source_unit, exponent))
            continue

        if target_unit not in UNIT_DEFS:
            new_units.append((source_unit, exponent))
            continue

        source_def = UNIT_DEFS[source_unit]
        target_def = UNIT_DEFS[target_unit]

        if source_def["dimension"] != target_def["dimension"]:
            new_units.append((source_unit, exponent))
            continue

        source_to_base = source_def["to_base"]
        target_to_base = target_def["to_base"]

        # If the old value is in source_unit^exponent,
        # converting to target_unit^exponent:
        #
        # new_value = old_value * (source_to_base / target_to_base)^exponent
        #
        # Example:
        #   1 m -> cm
        #   source_to_base = 1
        #   target_to_base = 0.01
        #   factor = 1 / 0.01 = 100
        #
        # Example:
        #   1 s^-1 -> ms^-1
        #   source_to_base = 1
        #   target_to_base = 0.001
        #   exponent = -1
        #   factor = (1 / 0.001)^-1 = 0.001
        factor = (source_to_base / target_to_base) ** exponent

        total_factor *= factor
        new_units.append((target_unit, exponent))

    new_value = value * total_factor

    return format_decimal(new_value), format_unit_expr(new_units)


def format_decimal(x: Decimal) -> str:
    """
    Reasonable compact formatting for scientific constants.
    """
    if x == 0:
        return "0"

    abs_x = abs(x)

    if abs_x >= Decimal("1e5") or abs_x < Decimal("1e-4"):
        s = f"{x:.8E}".replace("E", "e")
    else:
        s = format(x.normalize(), "f")

    s = s.replace("e+", "e")

    return s