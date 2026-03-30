from app.conexion_hv100 import make_instrument
from app.functions_read_write import safe_read_reg

inst = make_instrument()
inst.debug = True

print("PORT:", inst.serial.port)
print("BAUD:", inst.serial.baudrate)
print("BYTESIZE:", inst.serial.bytesize)
print("PARITY:", inst.serial.parity)
print("STOPBITS:", inst.serial.stopbits)
print("TIMEOUT:", inst.serial.timeout)
print("SLAVE:", inst.address)

try:
    valor = safe_read_reg(inst, 27393)
    print("VALOR:", valor)
except Exception as e:
    print("ERROR:", e)