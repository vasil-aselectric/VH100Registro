from app.conexion_hv100 import make_instrument, write_reg

inst = make_instrument()

registros = {
    7425: "d-00.00 = Frecuencia de referencia pantalla",
    27392: "11.00 = (0-MODBUS, 1-Definido por el usuario)",
    27393: "11.01 = Numero de esclavo",
    27394: "11.02 = Baud",
    27395: "11.03 = Data format",
    24845: "00.13 = Frecuencia maxima",
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
        write_reg(inst, addr, value)
        print(f"✅ Escrito {value} en {addr} ({registros[addr]})")
    except Exception as e:
        print(f"❌ Error escribiendo: {e}")