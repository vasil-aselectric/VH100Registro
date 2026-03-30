from app.conexion_hv100 import make_instrument, read_reg

inst = make_instrument()

registros = {7425: "d-00 = Frecuencia de referencia pantalla",
             7436: "d-12 =Voltaje del bus de CC (V)",
             7437: "d-13 =Tension de entrada",
             7466: "d-42 = Consigna en barres PID",
             7457: "d-33 = Temperatura del radiador 1",
             27392: "11.00 = (0-MODBUS, 1-Definido por el usuario)",
          
             27393: "11.01 = Numero de esclavo",
             27394: "11.02 = Bbaud (0: 2400BPS, 1: 4800BPS, 2: 9600BPS, 3: 19200BPS, 4: 38400BPS,5: 115200BPS)",
             27395: "11.03 = Date format (0: No check( N, 8,1)for RT)",
             24589: "00.13 = Frecuencia maxima",
             8193: "????? = Frecuencia de referencia Modbus",
             26625: "08.01 =  Selección de canal de configuración PID",
             

             }

for addr, desc in registros.items():
    value = read_reg(inst, addr)
    print(f"Rerstro decimal: {addr} | Valor actual: {value} | Descripción: {desc}")