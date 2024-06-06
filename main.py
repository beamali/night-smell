import socket
import threading
import time
import numpy as np
import json
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds


BRAIN_LIMIT_LOW = 0 + 0.1
BRAIN_LIMIT_HIGH = 100 - 0.1
MEASUREMENT_INDEX = 0
THETA_INDEX = 4


class BrainData:
    MUSCLE_LIMIT_LOW = 0 + 0.1
    MUSCLE_LIMIT_HIGH = 100 - 0.1
    BUFFER_PAUSE = 2

    def __init__(self):
        self.chan_in_use = [7, 8]
        self.ch_names = ['7', '8']
        self.demo_length = 60
        self.ch_types = ['eeg'] * len(self.chan_in_use)
        self.board = self.initial_board()
        self.data = []

    @property
    def params(self) -> BrainFlowInputParams:
        params = BrainFlowInputParams()
        params.serial_port = "/dev/cu.usbserial-DM03H3QF"
        params.buffer_length = 256
        return params

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

    def stream(self):
        threading.Thread(target=self.start_socket_stream).start()
        start_time = time.time()
        while time.time() - start_time < self.demo_length:
            continue
        average = np.mean(self.data)
        std = np.std(self.data)
        print(f"avarge:{average } std:{std}")

    def stop_stream(self):
        # No explicit stop needed for socket stream
        pass


def main():
    brain_data = BrainData()
    brain_data.stream()
    brain_data.stop_stream()


main()
