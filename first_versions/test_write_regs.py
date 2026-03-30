from app.conexion_hv100 import make_instrument, safe_write_reg

inst = make_instrument()



registros = {

   # Comunicación
    27393: [2, "11.01 = Numero de esclavo"],
    27394: [3, "11.02 = Baud"],
    27395: [0, "11.03 = Data format, (0: Sin verificación (N, 8, 1) para RTU)"],
    # Factory reset
     27392: [2, "14.12 = (0-MODBUS,
    # Parámetros de control
    27392: [0, "11.00 = (0-MODBUS, 1-Definido por el usuario)"],
    24589: [4, "00.13 = Frecuencia maxima"],
}

print("=== ESCRITURA REGISTROS HV100 ===")
print("Escribe 'xx' para salir\n")

while True:
    print("\nRegistros disponibles:")
    for addr, desc in registros.items():
        print(f"{addr} -> {desc}")

    user_addr = input("\nIntroduce dirección (ej: 7425) o 'xx': ")

    if user_addr.lower() == "xx":
        print("Saliendo...")
        break

    if not user_addr.isdigit():
        print("❌ Dirección inválida")
        continue

    addr = int(user_addr)

    if addr not in registros:
        print("❌ Registro no válido")
        continue

    user_value = input("Introduce valor a escribir: ")

    if not user_value.isdigit():
        print("❌ Valor inválido")
        continue

    value = int(user_value)

    try:
        safe_write_reg(inst, addr, value)
        print(f"✅ Escrito {value} en {addr} ({registros[addr]})")
    except Exception as e:
        print(f"❌ Error escribiendo: {e}")