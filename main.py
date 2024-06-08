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
SUBCUTANEOUS_CONDUCTION_LIMIT_HIGH = 20
MEASUREMENT_INDEX = 0
THETA_INDEX = 4
STD_LIMIT = 4.546125354443821


class BrainData:
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
        with open('initial_values.json', 'r') as file:
            return json.load(file)

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
        self.gsr_data += read_gsr_data_from_arduino()

    def stream(self, recording=False):
        threading.Thread(target=self.read_gsr_data_from_arduino).start()
        threading.Thread(target=self.start_socket_stream).start()
        start_time = time.time()
        while time.time() - start_time < self.demo_length:
            time.sleep(self.BUFFER_PAUSE)
            for i, theta_value in enumerate(self.data):
                try:
                    subcutaneous_conduction = self.gsr_data[i]
                    ypoints = np.array(self.gsr_data)
                    plt.plot(ypoints, linestyle='dotted')
                    plt.show()
                except IndexError:
                    continue
                if recording:
                    continue
                if theta_value >= BRAIN_LIMIT_HIGH + 2 * self.NORMAL_STD and subcutaneous_conduction >= SUBCUTANEOUS_CONDUCTION_LIMIT_HIGH:
                    print('measurement is too high')
                    self.run_relax_operation()
                    self.relaxing_mode = True
                elif (theta_value < 2 * self.NORMAL_STD or subcutaneous_conduction < SUBCUTANEOUS_CONDUCTION_LIMIT_HIGH):
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
