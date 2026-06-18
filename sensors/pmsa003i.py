import time
from typing import Optional, Dict, Any

import busio

# import digitalio  # only if you use a real reset pin
from adafruit_pm25.i2c import PM25_I2C


class PMSA003ISensor:

    def __init__(
        self,
        i2c: busio.I2C,
        reset_pin: Optional[Any] = None,
        *,
        max_retries: int = 5,
        retry_delay_sec: float = 2.0,
    ):
        self._pm25 = PM25_I2C(i2c, reset_pin)
        self._max_retries = max_retries
        self._retry_delay_sec = retry_delay_sec

    def _read_raw(self) -> Dict[str, Any]:
        last_exc = None
        for _ in range(self._max_retries):
            try:
                return self._pm25.read()
            except RuntimeError as e:
                last_exc = e
                time.sleep(self._retry_delay_sec)
        raise RuntimeError(
            f"Failed to read PMSA003I after {self._max_retries} attempts"
        ) from last_exc

    def read_telemetry(self) -> Dict[str, int]:
        aqdata = self._read_raw()

        return {
            "pm1_0": aqdata["pm10 standard"],
            "pm2_5": aqdata["pm25 standard"],
            "pm10": aqdata["pm100 standard"],
            "p_03": aqdata["particles 03um"],
            "p_05": aqdata["particles 05um"],
            "p_10": aqdata["particles 10um"],
            "p_25": aqdata["particles 25um"],
            "p_50": aqdata["particles 50um"],
            "p_100": aqdata["particles 100um"],
        }
