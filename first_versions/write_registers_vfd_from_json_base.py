import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.conexion_hv100 import make_instrument, with_modbus_lock


JSON_PATH = Path("JSON/base_and_variations.json")

# =========================
# SELECCIÓN ACTUAL
# =========================
SELECTED_USE_TYPE = "hibrido_pip"
SELECTED_PHASE_TYPE = "monofasico"
SELECTED_POWER_CODE = "202MH"

# Si True, escribe solo los parámetros con editable=True
WRITE_ONLY_EDITABLE = False

# Si quieres proteger algunos parámetros para no escribirlos nunca:
SKIP_PARAMS = {
    # "14.12",
}

# Valores especiales que no siguen la regla normal de decimales
PARAM_OVERRIDES = {
    "06.36": lambda value: 256, # este valor hex -> 100 en decimal
    "10.00": lambda value: 273, # este valor hex -> 273 en decimal
}

# Decimales por parámetro
PARAM_DECIMALS = {
    "00.04": 0,
    "00.12": 2,
    "00.13": 2,
    "00.14": 2,
    "00.16": 1,
    "00.17": 1,
    "02.01": 1,
    "02.02": 2,
    "02.04": 0,
    "02.05": 1,
    "06.36": 0,
    "08.10": 2,
    "08.17": 1,
    "08.18": 1,
    "08.24": 2,
    "10.00": 0,
    "10.21": 1,
    "10.22": 1,
    "12.05": 1,
    "12.07": 1,
    "16.00": 0,
    "16.01": 0,
    "16.02": 0,
    "16.03": 1,
    "16.04": 2,
}


def load_catalog(json_path: Path) -> Dict[str, Any]:
    if not json_path.exists():
        raise FileNotFoundError(f"No existe el archivo JSON: {json_path}")

    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if "base" not in data or not isinstance(data["base"], dict):
        raise ValueError("El JSON no tiene la clave 'base' o no es un objeto.")

    if "groups" not in data["base"] or not isinstance(data["base"]["groups"], list):
        raise ValueError("El JSON no tiene la clave 'base.groups' o no es una lista.")

    if "variations" not in data or not isinstance(data["variations"], dict):
        raise ValueError("El JSON no tiene la clave 'variations' o no es un objeto.")

    return data


def find_param_locations(groups: List[Dict[str, Any]], param_code: str) -> List[Dict[str, Any]]:
    matches = []

    for group_index, group in enumerate(groups):
        params = group.get("params", [])
        if not isinstance(params, list):
            continue

        for param_index, param in enumerate(params):
            if isinstance(param, dict) and param.get("param") == param_code:
                matches.append({
                    "group_index": group_index,
                    "param_index": param_index,
                    "param_obj": param
                })

    return matches


def apply_dict_override(groups: List[Dict[str, Any]], param_code: str, payload: Dict[str, Any]) -> None:
    matches = find_param_locations(groups, param_code)

    if not matches:
        print(f"WARNING: no encontré el parámetro {param_code} en base.groups")
        return

    # Para overrides normales, actualizamos el primer match
    target = matches[0]["param_obj"]

    if "value" in payload:
        target["value"] = payload["value"]

    if "others" in payload:
        target["others"] = payload["others"]

    if "description" in payload:
        target["description"] = payload["description"]

    if "editable" in payload:
        target["editable"] = payload["editable"]


def apply_list_override(groups: List[Dict[str, Any]], override_items: List[Dict[str, Dict[str, Any]]]) -> None:
    """
    Caso especial como hibrido_pip:
    [
      {"00.01": {"value": 1, "others": "PID"}},
      {"00.01": {"value": 4, "others": "SOLAR"}}
    ]

    Queremos conservar las dos escrituras secuenciales.
    """
    first_seen: Dict[str, bool] = {}

    for item in override_items:
        for param_code, payload in item.items():
            matches = find_param_locations(groups, param_code)

            if not matches:
                print(f"WARNING: no encontré el parámetro {param_code} para override tipo lista")
                continue

            if not first_seen.get(param_code, False):
                # Primera vez: actualizamos el primero existente
                target = matches[0]["param_obj"]

                if "value" in payload:
                    target["value"] = payload["value"]
                if "others" in payload:
                    target["others"] = payload["others"]
                if "description" in payload:
                    target["description"] = payload["description"]
                if "editable" in payload:
                    target["editable"] = payload["editable"]

                first_seen[param_code] = True
            else:
                # Siguientes veces: duplicamos el parámetro en el mismo grupo
                base_match = matches[0]
                new_param = copy.deepcopy(base_match["param_obj"])

                if "value" in payload:
                    new_param["value"] = payload["value"]
                if "others" in payload:
                    new_param["others"] = payload["others"]
                if "description" in payload:
                    new_param["description"] = payload["description"]
                if "editable" in payload:
                    new_param["editable"] = payload["editable"]

                group_idx = base_match["group_index"]
                groups[group_idx]["params"].append(new_param)


def build_resolved_config(
    catalog: Dict[str, Any],
    use_type: str,
    phase_type: str,
    power_code: str
) -> Dict[str, Any]:
    resolved = {
        "name": f"{catalog.get('metadata', {}).get('family', 'HV100')} {use_type} {phase_type} {power_code}",
        "groups": copy.deepcopy(catalog["base"]["groups"])
    }

    variations = catalog["variations"]

    # use_type
    use_variation = variations.get("use_type", {}).get(use_type)
    if use_variation is None:
        raise ValueError(f"No existe use_type '{use_type}' en el catálogo.")

    if isinstance(use_variation, list):
        apply_list_override(resolved["groups"], use_variation)
    elif isinstance(use_variation, dict):
        for param_code, payload in use_variation.items():
            apply_dict_override(resolved["groups"], param_code, payload)
    else:
        raise ValueError(f"Formato inválido en variations.use_type.{use_type}")

    # phase_type
    phase_variation = variations.get("phase_type", {}).get(phase_type)
    if phase_variation is None:
        raise ValueError(f"No existe phase_type '{phase_type}' en el catálogo.")

    for param_code, payload in phase_variation.items():
        apply_dict_override(resolved["groups"], param_code, payload)

    # power_kw / power_code
    power_variation = variations.get("power_kw", {}).get(power_code)
    if power_variation is None:
        raise ValueError(f"No existe power_code '{power_code}' en el catálogo.")

    for param_code, payload in power_variation.items():
        apply_dict_override(resolved["groups"], param_code, payload)

    return resolved


def iter_params(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for group in config.get("groups", []):
        group_name = group.get("group_section", "SIN_GRUPO")
        params = group.get("params", [])

        if not isinstance(params, list):
            continue

        for param in params:
            if not isinstance(param, dict):
                continue

            rows.append({
                "group_section": group_name,
                "param": param.get("param"),
                "value": param.get("value"),
                "address_decimal": param.get("address_decimal"),
                "others": param.get("others", ""),
                "description": param.get("description", ""),
                "editable": param.get("editable", False),
            })

    return rows


def filter_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered: List[Dict[str, Any]] = []

    for row in rows:
        param = row.get("param")
        if not param:
            continue

        if param in SKIP_PARAMS:
            continue

        if WRITE_ONLY_EDITABLE and not row.get("editable", False):
            continue

        if row.get("address_decimal") is None:
            continue

        filtered.append(row)

    return filtered


def get_decimals(param: str) -> int:
    return PARAM_DECIMALS.get(param, 0)


def get_raw_value(param: str, value: Any, decimals: int) -> int:
    if param in PARAM_OVERRIDES:
        return PARAM_OVERRIDES[param](value)

    numeric = float(value)
    factor = 10 ** decimals
    return int(round(numeric * factor))


def read_raw_reg(inst, addr: int) -> int:
    return with_modbus_lock(
        lambda: inst.read_register(addr, number_of_decimals=0, functioncode=3, signed=False)
    )


def write_raw_reg(inst, addr: int, raw_value: int, fc: int = 6) -> None:
    return with_modbus_lock(
        lambda: inst.write_register(
            addr,
            raw_value,
            number_of_decimals=0,
            functioncode=fc,
            signed=False,
        )
    )


def main() -> None:
    catalog = load_catalog(JSON_PATH)

    config = build_resolved_config(
        catalog=catalog,
        use_type=SELECTED_USE_TYPE,
        phase_type=SELECTED_PHASE_TYPE,
        power_code=SELECTED_POWER_CODE
    )

    rows = iter_params(config)
    rows = filter_rows(rows)

    inst = make_instrument()

    print(f"Configuración resuelta: {config.get('name', 'SIN_NOMBRE')}")
    print(f"Total escrituras finales: {len(rows)}")
    print("-" * 100)

    for row in rows:
        param = row["param"]
        addr = row["address_decimal"]
        value_human = row["value"]
        decimals = get_decimals(param)
        raw_to_write = get_raw_value(param, value_human, decimals)

        try:
            before_raw = read_raw_reg(inst, addr)
            write_raw_reg(inst, addr, raw_to_write)
            after_raw = read_raw_reg(inst, addr)

            status = "OK" if after_raw == raw_to_write else "ERROR"

            print(
                f"{param} | addr={addr} | "
                f"json={value_human} | dec={decimals} | "
                f"raw_before={before_raw} | raw_write={raw_to_write} | raw_after={after_raw} | "
                f"{status}"
            )

        except Exception as e:
            print(
                f"{param} | addr={addr} | json={value_human} | dec={decimals} | ERROR: {e}"
            )


if __name__ == "__main__":
    main()