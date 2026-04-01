import minimalmodbus
import serial
import portalocker

# CONFIG HV100 (VIA WINDOWS) - NO TOCAR
# VFD_PORT = "COM8"

# CONFIG HV100 (VIA RASPBERRYPI) - NO TOCAR
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
    inst.serial.parity = serial.PARITY_EVEN
    inst.serial.stopbits = 1
    inst.serial.timeout = 2
    inst.mode = minimalmodbus.MODE_RTU
    inst.clear_buffers_before_each_transaction = True
    inst.close_port_after_each_call = True
    inst.debug = False
    return inst