import serial

ser = serial.Serial("COM8", 19200)
print("OK")
ser.close()