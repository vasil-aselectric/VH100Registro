from app.conexion_hv100 import make_instrument, read_reg

inst = make_instrument()

registros = {7425: "d-00.00 = Frecuencia de referencia pantalla",
             27392: "11.00 = (0-MODBUS, 1-Definido por el usuario)",
             27393: "11.01 = Numero de esclavo",
             27394: "11.02 = Bbaud (0: 2400BPS, 1: 4800BPS, 2: 9600BPS, 3: 19200BPS, 4: 38400BPS,5: 115200BPS)",
             27395: "11.03 = Date format (0: No check( N, 8,1)for RT)",
             24845: "00.13 = Frecuencia maxima",
             
             }

for addr in [7425, 27392, 27393, 27394, 27395]:
    value = read_reg(inst, registros[addr].split(" = ")[0].split(".")[1])
    print(addr, value)