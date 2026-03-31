from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


# =========================
# RUTAS PROYECTO
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent
JSON_DIR = BASE_DIR / "JSON"
INTERFACE_DIR = BASE_DIR / "interface"

CATALOG_PATH = JSON_DIR / "base_and_variations.json"


# =========================
# APP FASTAPI
# =========================
app = FastAPI(title="HV100 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # luego lo cerramos si quieres
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Archivos estáticos del frontend
app.mount("/assets", StaticFiles(directory=INTERFACE_DIR / "assets"), name="assets")
app.mount("/JSON", StaticFiles(directory=JSON_DIR), name="json")


# =========================
# MODELOS
# =========================
class InverterSelection(BaseModel):
    use_type: str
    phase_type: str
    power_code: str


# =========================
# HELPERS JSON
# =========================
def load_catalog() -> Dict[str, Any]:
    if not CATALOG_PATH.exists():
        raise FileNotFoundError(f"No existe el catálogo: {CATALOG_PATH}")

    with CATALOG_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if "base" not in data or not isinstance(data["base"], dict):
        raise ValueError("El catálogo no tiene la clave 'base' o no es un objeto.")

    if "groups" not in data["base"] or not isinstance(data["base"]["groups"], list):
        raise ValueError("El catálogo no tiene la clave 'base.groups' o no es una lista.")

    if "variations" not in data or not isinstance(data["variations"], dict):
        raise ValueError("El catálogo no tiene la clave 'variations' o no es un objeto.")

    return data


def find_param_locations(groups: List[Dict[str, Any]], param_code: str) -> List[Dict[str, Any]]:
    matches: List[Dict[str, Any]] = []

    for group_index, group in enumerate(groups):
        params = group.get("params", [])
        if not isinstance(params, list):
            continue

        for param_index, param in enumerate(params):
            if isinstance(param, dict) and param.get("param") == param_code:
                matches.append(
                    {
                        "group_index": group_index,
                        "param_index": param_index,
                        "param_obj": param,
                    }
                )

    return matches


def apply_dict_override(groups: List[Dict[str, Any]], param_code: str, payload: Dict[str, Any]) -> None:
    matches = find_param_locations(groups, param_code)

    if not matches:
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
    """
    Soporta casos como:
    [
      {"00.01": {"value": 1, "others": "PID"}},
      {"00.01": {"value": 4, "others": "SOLAR"}}
    ]
    """
    first_seen: Dict[str, bool] = {}

    for item in override_items:
        for param_code, payload in item.items():
            matches = find_param_locations(groups, param_code)

            if not matches:
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


def build_variant_code(use_type: str, phase_type: str, power_code: str) -> str:
    use_prefix = "HIBRIDO" if use_type == "hibrido_pip" else "CLASICO"
    phase_prefix = "MONO" if phase_type == "monofasico" else "TRI"
    return f"{use_prefix}_{phase_prefix}_{power_code}"


def build_resolved_config(
    catalog: Dict[str, Any],
    use_type: str,
    phase_type: str,
    power_code: str,
) -> Dict[str, Any]:
    resolved = {
        "name": f"{catalog.get('metadata', {}).get('family', 'HV100')} {use_type} {phase_type} {power_code}",
        "groups": copy.deepcopy(catalog["base"]["groups"]),
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

    # power_code
    power_variation = variations.get("power_kw", {}).get(power_code)
    if power_variation is None:
        raise ValueError(f"No existe power_code '{power_code}' en el catálogo.")

    for param_code, payload in power_variation.items():
        apply_dict_override(resolved["groups"], param_code, payload)

    return resolved


def get_catalog_options(catalog: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "use_types": list(catalog.get("variations", {}).get("use_type", {}).keys()),
        "phase_types": list(catalog.get("variations", {}).get("phase_type", {}).keys()),
        "power_codes": list(catalog.get("variations", {}).get("power_kw", {}).keys()),
    }


# =========================
# ENDPOINTS
# =========================
@app.get("/")
def serve_index() -> FileResponse:
    index_path = INTERFACE_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="No existe interface/index.html")
    return FileResponse(index_path)


@app.get("/api/v1/inverter/catalog")
def get_catalog() -> Dict[str, Any]:
    try:
        catalog = load_catalog()
        return {
            "ok": True,
            "metadata": catalog.get("metadata", {}),
            "options": get_catalog_options(catalog),
            "raw_catalog": catalog,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/inverter/select")
def select_inverter(payload: InverterSelection) -> Dict[str, Any]:
    try:
        catalog = load_catalog()

        resolved_config = build_resolved_config(
            catalog=catalog,
            use_type=payload.use_type,
            phase_type=payload.phase_type,
            power_code=payload.power_code,
        )

        variant_code = build_variant_code(
            use_type=payload.use_type,
            phase_type=payload.phase_type,
            power_code=payload.power_code,
        )

        return {
            "ok": True,
            "variant_code": variant_code,
            "selection": payload.model_dump(),
            "resolved_config": resolved_config,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/inverter/apply")
def apply_inverter_config(payload: InverterSelection) -> Dict[str, Any]:
    """
    Endpoint reservado para el siguiente paso:
    - construir resolved_config
    - lanzar escritura Modbus real
    """
    try:
        catalog = load_catalog()

        resolved_config = build_resolved_config(
            catalog=catalog,
            use_type=payload.use_type,
            phase_type=payload.phase_type,
            power_code=payload.power_code,
        )

        variant_code = build_variant_code(
            use_type=payload.use_type,
            phase_type=payload.phase_type,
            power_code=payload.power_code,
        )

        return {
            "ok": True,
            "message": "Endpoint preparado. Falta conectar la escritura Modbus real.",
            "variant_code": variant_code,
            "selection": payload.model_dump(),
            "resolved_config": resolved_config,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))