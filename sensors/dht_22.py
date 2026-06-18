from time import sleep
from typing import Dict

import adafruit_dht
import board


class DHT22:
    def __init__(self, pin: board.Pin):
        self.__pin = pin
        self._dht = adafruit_dht.DHT22(pin, use_pulseio=False)

    def read_telemetry(self) -> Dict[str, float]:
        context = {"temperature": self._dht.temperature, "humidity": self._dht.humidity}

        for i in range(5):  # try five times before error
            try:
                return context
            except RuntimeError:
                sleep(2.0)
                pass
        raise RuntimeError("Failed to reed temperature from DHT-25")
