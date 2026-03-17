from app.conexion_hv100 import make_instrument, read_reg

inst = make_instrument()

for addr in [27392, 27393, 27394, 27395]:
    value = read_reg(inst, addr)
    print(addr, value)