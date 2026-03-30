import json
from pathlib import Path
from typing import Any, Dict, List

from app.conexion_hv100 import make_instrument
from app.functions_read_write import safe_read_reg

JSON_PATH = Path("JSON/config_hibrido_pid_202mh.json")


def load_json_config(json_path: Path) -> Dict[str, Any]:
    if not json_path.exists():
        raise FileNotFoundError(f"No existe el archivo JSON: {json_path}")

    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if "groups" not in data or not isinstance(data["groups"], list):
        raise ValueError("El JSON no tiene la clave 'groups' o no es una lista.")

    return data


def iter_params(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    result = []

    for group in config.get("groups", []):
        group_name = group.get("group_section", "SIN_GRUPO")
        params = group.get("params", [])

        if not isinstance(params, list):
            continue

        for param in params:
            if not isinstance(param, dict):
                continue

            result.append({
                "group_section": group_name,
                "param": param.get("param"),
                "value": param.get("value"),
                "address_decimal": param.get("address_decimal"),
                "others": param.get("others", ""),
                "description": param.get("description", ""),
                "editable": param.get("editable", False),
            })

    return result


def build_register_cache(inst: Any, params: List[Dict[str, Any]]) -> Dict[int, Any]:
    unique_addresses = {
        item["address_decimal"]
        for item in params
        if item.get("address_decimal") is not None
    }

    cache: Dict[int, Any] = {}

    for addr in sorted(unique_addresses):
        try:
            cache[addr] = safe_read_reg(inst, addr)
        except Exception as e:
            cache[addr] = f"ERROR: {e}"

    return cache


def main() -> None:
    config = load_json_config(JSON_PATH)
    inst = make_instrument()
    params = iter_params(config)
    cache = build_register_cache(inst, params)

    print(f"Nombre configuración: {config.get('name', 'SIN_NOMBRE')}")
    print(f"Total parámetros: {len(params)}")
    print(f"Total direcciones únicas leídas: {len(cache)}")
    print("-" * 120)

    for item in params:
        addr = item["address_decimal"]
        valor_actual = cache.get(addr, "SIN_LECTURA")

        print(
            f"Grupo: {item['group_section']} | "
            f"Param: {item['param']} | "
            f"Valor JSON: {item['value']} | "
            f"Address Decimal: {addr} | "
            f"Valor actual: {valor_actual} | "
            f"Others: {item['others']} | "
            f"Descripción: {item['description']} | "
            f"Editable: {item['editable']}"
        )


if __name__ == "__main__":
    main()