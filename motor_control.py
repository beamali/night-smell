import serial
import serial.tools.list_ports


def select_arudino_port() -> str | None:
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "Arduino" in port.description:
            return port.device
    return None


ARDUINO_PORT = "/dev/cu.usbserial-110"
print(ARDUINO_PORT)
if ARDUINO_PORT is None:
    raise ValueError("No Arduino found")
ser = serial.Serial(ARDUINO_PORT, 9600)


def start_arduino_motor(port: str = ARDUINO_PORT):
    ser.write(b'S')


def stop_arduino_motor(port: str = ARDUINO_PORT):
    ser.write(b'P')


def read_gsr_data_from_arduino(port: str = ARDUINO_PORT) -> list[bytes]:
    data = []
    try:
        while ser.in_waiting:
            data.append(int(ser.readline()))
    except Exception as e:
        pass
    return data
