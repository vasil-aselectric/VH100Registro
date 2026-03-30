import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.conexion_hv100 import make_instrument, with_modbus_lock

JSON_PATH = Path("JSON/config_hibrido_pid_202mh.json")

# Si True, escribe solo los parámetros con editable=True
# Si False, escribe todo lo seleccionado del JSON
WRITE_ONLY_EDITABLE = False

# Resolver parámetros duplicados del JSON
SELECTION_BY_PARAM = {
    "00.01": "SOLAR",
    "07.02": "PARADA POR FALTA DE AGUA NC",
}

# Valores especiales que no siguen la regla normal de decimales
PARAM_OVERRIDES = {
    "06.36": lambda value: 256, # este valor hex -> 100 en decimal
    "10.00": lambda value: 273, # este valor hex -> 273 en decimal
}

# Decimales por parámetro SIN tocar el JSON
# Los que no aparezcan aquí se tratan como enteros (0 decimales)
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
    "15.07": 2,
    "16.00": 0,
    "16.01": 0,
    "16.02": 0,
    "16.03": 1,
    "16.04": 2,
}

# Parámetros que no quieres escribir nunca
SKIP_PARAMS = {
    "14.12",  # reset default
}


def load_json_config(json_path: Path) -> Dict[str, Any]:
    if not json_path.exists():
        raise FileNotFoundError(f"No existe el archivo JSON: {json_path}")

    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if "groups" not in data or not isinstance(data["groups"], list):
        raise ValueError("El JSON no tiene la clave 'groups' o no es una lista.")

    return data


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


def normalize_text(text: str) -> str:
    return " ".join(str(text).strip().upper().split())


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


def resolve_duplicates(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_param: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_param[row["param"]].append(row)

    resolved: List[Dict[str, Any]] = []

    for param, items in by_param.items():
        if len(items) == 1:
            resolved.append(items[0])
            continue

        values = {str(item["value"]) for item in items}
        if len(values) == 1:
            resolved.append(items[0])
            continue

        wanted = SELECTION_BY_PARAM.get(param)
        if wanted is None:
            print(f"SKIP DUPLICADO {param} -> falta resolver en SELECTION_BY_PARAM")
            for item in items:
                print(
                    f"    - {item['param']} | {item['value']} | "
                    f"{item['description']} | {item['others']}"
                )
            continue

        wanted_norm = normalize_text(wanted)
        selected: Optional[Dict[str, Any]] = None

        for item in items:
            haystack = normalize_text(f"{item['description']} {item['others']}")
            if wanted_norm in haystack:
                selected = item
                break

        if selected is None:
            print(f"SKIP DUPLICADO {param} -> no encontré coincidencia para '{wanted}'")
            for item in items:
                print(
                    f"    - {item['param']} | {item['value']} | "
                    f"{item['description']} | {item['others']}"
                )
            continue

        resolved.append(selected)

    return resolved


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
    config = load_json_config(JSON_PATH)
    rows = iter_params(config)
    rows = filter_rows(rows)
    jobs = resolve_duplicates(rows)

    inst = make_instrument()

    print(f"Configuración: {config.get('name', 'SIN_NOMBRE')}")
    print(f"Total líneas JSON: {len(rows)}")
    print(f"Total escrituras finales: {len(jobs)}")
    print("-" * 100)

    for row in jobs:
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