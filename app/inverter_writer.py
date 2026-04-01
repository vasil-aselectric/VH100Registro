import time
from typing import Any, Dict, List

from app.conexion_hv100 import make_instrument, with_modbus_lock


PARAM_OVERRIDES = {
    "06.36": lambda value: 256, # este valor hex -> 100 en decimal
    "10.00": lambda value: 273, # este valor hex -> 273 en decimal
}

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

SKIP_PARAMS = set()


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


def write_config_to_vfd(config: Dict[str, Any]) -> Dict[str, Any]:
    inst = make_instrument()
    rows = iter_params(config)

    results = []

    for row in rows:
        param = row["param"]
        addr = row["address_decimal"]
        value_human = row["value"]

        if not param or addr is None or param in SKIP_PARAMS:
            continue

        if value_human is None:
            results.append({
                "param": param,
                "addr": addr,
                "status": "SKIPPED",
                "reason": "value is None"
            })
            continue

        decimals = get_decimals(param)
        raw_to_write = get_raw_value(param, value_human, decimals)

        try:
            before_raw = read_raw_reg(inst, addr)
            time.sleep(0.05)
            write_raw_reg(inst, addr, raw_to_write)
            time.sleep(0.05)
            after_raw = read_raw_reg(inst, addr)
            time.sleep(0.05)
            status = "OK" if after_raw == raw_to_write else "ERROR"

            results.append({
                "param": param,
                "addr": addr,
                "value_json": value_human,
                "decimals": decimals,
                "raw_before": before_raw,
                "raw_write": raw_to_write,
                "raw_after": after_raw,
                "status": status,
                "group_section": row["group_section"],
                "description": row["description"],
            })
        except Exception as e:
            results.append({
                "param": param,
                "addr": addr,
                "value_json": value_human,
                "decimals": decimals,
                "status": "ERROR",
                "error": str(e),
                "group_section": row["group_section"],
                "description": row["description"],
            })
            time.sleep(0.05)
            
        finally:
            try:
                inst.serial.close()
            except Exception:
                pass


    ok_count = sum(1 for r in results if r["status"] == "OK")
    error_count = sum(1 for r in results if r["status"] == "ERROR")

    return {
        "ok": error_count == 0,
        "total": len(results),
        "ok_count": ok_count,
        "error_count": error_count,
        "results": results,
    }