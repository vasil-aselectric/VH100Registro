from app.conexion_hv100 import with_modbus_lock, minimalmodbus


def read_reg(inst: minimalmodbus.Instrument, addr: int) -> int:
    return inst.read_register(addr, number_of_decimals=0, functioncode=3, signed=False)


def write_reg(inst: minimalmodbus.Instrument, addr: int, value: int, fc: int = 6) -> None:
    inst.write_register(addr, value, number_of_decimals=0, functioncode=fc, signed=False)


def safe_read_reg(inst: minimalmodbus.Instrument, addr: int) -> int:
    return with_modbus_lock(lambda: read_reg(inst, addr))


def safe_write_reg(inst: minimalmodbus.Instrument, addr: int, value: int, fc: int = 6) -> None:
    return with_modbus_lock(lambda: write_reg(inst, addr, value, fc))