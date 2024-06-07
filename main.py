import socket
import sqlite3
import threading
import time
import numpy as np
import json
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

from motor_control import start_arduino_motor, stop_arduino_motor

BRAIN_LIMIT_LOW = 0 + 0.1
BRAIN_LIMIT_HIGH = 100 - 0.1
MEASUREMENT_INDEX = 0
THETA_INDEX = 4


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

    def stream(self, recording=False):
        threading.Thread(target=self.start_socket_stream).start()
        start_time = time.time()
        while time.time() - start_time < self.demo_length:
            time.sleep(self.BUFFER_PAUSE)
            for i in self.data:
                if recording:
                  self.save_results(i)
                  continue
                if i > 2 * self.NORMAL_STD:
                    print('measurement is too high')
                    self.run_relax_operation()
                    self.relaxing_mode = True
                if i < 2 * self.NORMAL_STD and self.relaxing_mode:
                    self.return_to_normal()
                    self.relaxing_mode = False
                self.save_results(i)

        average = np.mean(self.data)
        std = np.std(self.data)
        print(f"avarge:{average } std:{std}")
        return average, std

    def save_results(self, theta_value, subcutaneous_conduction):
        conn = sqlite3.connect('night-smell.db')
        cursor = conn.cursor()
        cursor.executemany('''
        INSERT INTO records (date, subcutaneous_conduction, theta_value, is_relax_mode_activated)
        VALUES (?, ?, ?, ?)
        ''', time.time(), subcutaneous_conduction, theta_value, int(self.relaxing_mode))


def main(recording=False):
    brain_data = BrainData()
    brain_data.stream(recording)


main()
