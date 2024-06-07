import socket
import sqlite3
import threading
import time

import numpy as np
import json
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
from matplotlib import pyplot as plt, animation

from motor_control import read_gsr_data_from_arduino, stop_arduino_motor, start_arduino_motor

BRAIN_LIMIT_HIGH = 0.5
SUBCUTANEOUS_CONDUCTION_LIMIT_HIGH = 400
MEASUREMENT_INDEX = 0
THETA_INDEX = 4
STD_LIMIT = 4.546125354443821


class BrainData:
    MUSCLE_LIMIT_LOW = 0 + 0.1
    MUSCLE_LIMIT_HIGH = 100 - 0.1
    BUFFER_PAUSE = 2
    NORMAL_STD = 0.5

    def __init__(self):
        self.chan_in_use = [7, 8]
        self.ch_names = ['7', '8']
        self.demo_length = 60
        self.ch_types = ['eeg'] * len(self.chan_in_use)
        self.board = self.initial_board()
        self.data = []
        self.relaxing_mode = False
        self.motor_last_change_time = time.time()
        self.motor_started = False
        self.gsr_data = []
        self.fig, self.ax = plt.subplots()
        self.float_values = []
        self.line, = self.ax.plot(self.float_values)

    def update_subcutaneous_conduction_graph(self, new_value):
        # Append the new value to the list
        self.float_values.append(new_value)

        # Update the data of the line object
        self.line.set_ydata(self.float_values)
        self.line.set_xdata(range(len(self.float_values)))

        # Set the limits of the plot
        self.ax.set_xlim(0, len(self.float_values))
        self.ax.set_ylim(0, 10)

        return self.line,

    @property
    def params(self) -> BrainFlowInputParams:
        params = BrainFlowInputParams()
        params.serial_port = "/dev/cu.usbserial-DM03H3QF"
        params.buffer_length = 256
        return params

    @classmethod
    def run_relax_operation(cls):
        start_arduino_motor()

    @classmethod
    def return_to_normal(cls):
        stop_arduino_motor()

    def get_initial_value(self):
        conn = sqlite3.connect('night-smell.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM initial_values')
        return cursor.fetchone()

    def initial_board(self) -> BoardShim:
        params = BrainFlowInputParams()
        board = BoardShim(BoardIds.CYTON_BOARD, self.params)
        params.sfreq = board.get_sampling_rate(board.get_board_id())
        return board

    def start_socket_stream(self):
        host = 'localhost'
        port = 12345
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((host, port))

        try:
            while True:
                data = sock.recvfrom(1024)
                if not data:
                    print('No data received')
                    return sock
                for measurement in json.loads(data[MEASUREMENT_INDEX])["data"]:
                    self.data.append(measurement[THETA_INDEX])
                    print(measurement[THETA_INDEX])
                if len(self.data) > 100:
                    self.data.pop(0)
        finally:
            sock.close()

    def read_gsr_data_from_arduino(self) -> None:
        print("Data is", read_gsr_data_from_arduino())
        self.gsr_data += read_gsr_data_from_arduino()

    def stream(self, recording=False):
        threading.Thread(target=self.start_socket_stream).start()
        threading.Thread(target=self.read_gsr_data_from_arduino).start()
        start_time = time.time()
        while time.time() - start_time < self.demo_length:
            time.sleep(self.BUFFER_PAUSE)
            for i, theta_value in enumerate(self.data):
                try:
                    subcutaneous_conduction = self.gsr_data[i]
                    ani = animation.FuncAnimation(self.fig, self.update_subcutaneous_conduction_graph, frames=self.gsr_data, blit=True)
                    plt.show()
                except IndexError:
                    continue
                if recording:
                    continue
                if i >= BRAIN_LIMIT_HIGH + 2 * self.NORMAL_STD and subcutaneous_conduction >= SUBCUTANEOUS_CONDUCTION_LIMIT_HIGH:
                    print('measurement is too high')
                    self.run_relax_operation()
                    self.relaxing_mode = True
                elif i < 2 * self.NORMAL_STD and self.relaxing_mode or subcutaneous_conduction < SUBCUTANEOUS_CONDUCTION_LIMIT_HIGH:
                    self.return_to_normal()
                    self.relaxing_mode = False
                self.save_results(theta_value=theta_value, subcutaneous_conduction=subcutaneous_conduction)
        if recording:
            average = np.mean(self.data)
            std = np.std(self.data)
            self.save_inital_value(average, std)

    def save_results(self, theta_value, subcutaneous_conduction):
        with open('results.json', 'a') as file:
            json.dump({'theta_value': theta_value, 'subcutaneous_conduction': subcutaneous_conduction, "date": time.time(), "is_relax_mode_activated": self.relaxing_mode}, file)

    def save_inital_value(self, average, std):
        with open('initial_values.json', 'w') as file:
            json.dump({'average': average, 'std': std}, file)


def main(recording=False):
    brain_data = BrainData()
    brain_data.stream(recording)


main()
