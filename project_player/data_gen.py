import random
import threading
import time

class DataGen:
    def __init__(self):
        self.lock = threading.Lock()

    def _gauss(self, mu, sigma):
        return round(random.gauss(mu, sigma), 2)

    def _prob(self, p):
        return random.random() < p

    def get_single_device_packet(self, device_id, sig_in, vol_in, bass_in, like_p):
        packet = {
            'id': device_id,
            'signal': self._gauss(*sig_in),
            'volume': self._gauss(*vol_in),
            'bass': self._gauss(*bass_in),
            'like': self._prob(like_p),
            'time': time.strftime('%H:%M:%S')
        }
        return packet