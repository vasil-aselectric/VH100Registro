import minimalmodbus
import serial
import portalocker

# CONFIG HV100
VFD_PORT = "/dev/ttyUSB3"
VFD_BAUD = 19200
VFD_SLAVE_ID = 1

LOCK_FILE = "modbus_vfd.lock"

def with_modbus_lock(fn):
    with open(LOCK_FILE, "w") as f:
        portalocker.lock(f, portalocker.LOCK_EX)
        try:
            return fn()
        finally:
            portalocker.unlock(f)

def make_instrument() -> minimalmodbus.Instrument:
    inst = minimalmodbus.Instrument(VFD_PORT, VFD_SLAVE_ID)
    inst.serial.baudrate = VFD_BAUD
    inst.serial.bytesize = 8
    inst.serial.parity = serial.PARITY_NONE
    inst.serial.stopbits = 1
    inst.serial.timeout = 2
    inst.mode = minimalmodbus.MODE_RTU
    inst.clear_buffers_before_each_transaction = True
    inst.debug = False
    return inst

def read_reg(inst: minimalmodbus.Instrument, addr: int) -> int:
    return int(inst.read_register(addr, 0, functioncode=3, signed=False))

def safe_read_reg(inst: minimalmodbus.Instrument, addr: int) -> int:
    return with_modbus_lock(lambda: read_reg(inst, addr))

def write_reg(inst: minimalmodbus.Instrument, addr: int, value: int, fc: int = 6) -> None:
    inst.write_register(addr, int(value), number_of_decimals=0, functioncode=fc, signed=False)

def safe_write_reg(inst: minimalmodbus.Instrument, addr: int, value: int, fc: int = 6) -> None:
    return with_modbus_lock(lambda: write_reg(inst, addr, value, fc))