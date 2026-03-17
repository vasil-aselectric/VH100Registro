from app.conexion_hv100 import make_instrument, read_reg

inst = make_instrument()

for addr in [7425]:
    value = read_reg(inst, addr)
    print(addr, value)