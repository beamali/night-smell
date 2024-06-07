import serial
import serial.tools.list_ports


def select_arudino_port() -> str | None:
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "Arduino" in port.description:
            return port.device
    return None


ARDUINO_PORT = select_arudino_port()


def start_arduino_motor(port: str = ARDUINO_PORT):
    ser = serial.Serial(port, 9600)

    ser.write(bytearray([10]))


def stop_arduino_motor(port: str = ARDUINO_PORT):
    ser = serial.Serial(port, 9600)

    ser.write(bytearray([20]))
