import sys
import json
import copy
from pathlib import Path
from typing import Any, Dict, List

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.conexion_hv100 import make_instrument
from app.functions_read_write import safe_read_reg


JSON_PATH = Path(__file__).resolve().parents[1] / "JSON" / "base_and_variations.json"

# =========================
# SELECCIÓN ACTUAL
# =========================
SELECTED_USE_TYPE = "hibrido_pip"
SELECTED_PHASE_TYPE = "monofasico"
SELECTED_POWER_CODE = "202MH"


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
    first_seen: Dict[str, bool] = {}

    for item in override_items:
        for param_code, payload in item.items():
            matches = find_param_locations(groups, param_code)

            if not matches:
                print(f"WARNING: no encontré el parámetro {param_code} para override tipo lista")
                continue

            if not first_seen.get(param_code, False):
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

            addr = param.get("address_decimal")
            if addr is None:
                continue

            rows.append({
                "group_section": group_name,
                "param": param.get("param"),
                "value": param.get("value"),
                "address_decimal": addr,
                "others": param.get("others", ""),
                "description": param.get("description", ""),
                "editable": param.get("editable", False),
            })

    return rows


def main() -> None:
    catalog = load_catalog(JSON_PATH)

    config = build_resolved_config(
        catalog=catalog,
        use_type=SELECTED_USE_TYPE,
        phase_type=SELECTED_PHASE_TYPE,
        power_code=SELECTED_POWER_CODE
    )

    rows = iter_params(config)
    inst = make_instrument()

    print(f"JSON: {JSON_PATH}")
    print(f"Configuración resuelta: {config.get('name', 'SIN_NOMBRE')}")
    print(f"Total registros a leer: {len(rows)}")
    print("-" * 140)

    for row in rows:
        addr = row["address_decimal"]
        param = row["param"]
        value_json = row["value"]
        description = row["description"]
        others = row["others"]
        group_section = row["group_section"]

        try:
            value_real = safe_read_reg(inst, addr)

            if value_json is not None and value_real != value_json:
                print(
                    f"Param: {param:<6} | "
                    f"Valor lectura: {str(value_real):<6} | "
                    f"Valor JSON: {str(value_json):<6} | "
                    f"Desc: {description:<40}"
                )
        except Exception as e:
            print(
            f"Param: {param:<6} | "
            f"Addr: {addr:<6} | "
            f"ERROR leyendo: {str(e):<40} | "
            f"Desc: {description}"
        )


if __name__ == "__main__":
    main()