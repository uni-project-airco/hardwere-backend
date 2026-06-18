import asyncio
from time import sleep
from typing import Dict

import requests

from config import *
from utils import (
    read_telemetry_data,
    send_alerts,
    send_telemetry_update,
    listen_pubnub_messages,
)


def pubnub_channel_boot(cfg: Dict) -> None:
    if cfg["pubnub"]["channel-name"] is None:
        url: str = f"{cfg['server-url']}/sensor/register"
        response: requests.Response = requests.post(
            url=url,
            json={
                "sensor-id": cfg["sensor-id"],
            },
            headers={
                "certificate-string": cfg["certificate-string"],
                "sensor-id": cfg["sensor-id"],
            },
        )
        if not response.ok:
            raise RuntimeError("Device certification failed")

        cfg["pubnub"]["channel-name"] = response.json()["channel"]
        cfg["pubnub"]["access-token"] = response.json()["token"]


def boot(cfg: Dict) -> Dict:
    # TODO connect to home wifi if not registered
    # wifi_boot()

    pubnub_channel_boot(cfg)
    return cfg


async def run(cfg: JSON_DATA):
    t_writer = asyncio.create_task(read_telemetry_data())
    t_alerts = asyncio.create_task(send_alerts(cfg))
    t_update = asyncio.create_task(send_telemetry_update(cfg))
    t_pubnub_listener = asyncio.create_task(listen_pubnub_messages())

    try:
        while True:
            calculations = {
                "temperature": 0,
                "humidity": 0,
                "co2": 0,
                "pm25": 0,
            }
            for i in range(6):  # total 10 minutes
                for key, value in shared_state.items():
                    calculations[key] += value
                sleep(2 * 60)
            response = requests.post(
                url=f'{cfg["server-url"]}/telemetry/save_telemetry',
                json={
                    "temperature": round(calculations["temperature"] / 5),
                    "humidity": round(calculations["humidity"] / 5),
                    "co2": round(calculations["co2"] / 5),
                    "pm25": round(calculations["pm25"] / 5),
                },
                headers={
                    "certificate-string": cfg["certificate-string"],
                    "sensor-id": cfg["sensor-id"],
                },
            )

            logger.info(f"Telemetry sent - {response.status_code}")
    except Exception as e:
        logger.error(e)

        t_writer.cancel()
        t_alerts.cancel()
        t_update.cancel()
        t_pubnub_listener.cancel()


if __name__ == "__main__":
    logger.info("Program launched")
    cfg = load_config(CONFIG_PATH)
    cfg = boot(cfg)
    save_config(CONFIG_PATH, cfg)
    cfg = load_config(CONFIG_PATH)
    CURRENT_THRESHOLDS = cfg["thresholds"]

    asyncio.run(run(cfg))
