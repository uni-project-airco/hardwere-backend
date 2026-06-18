import asyncio
from typing import Dict

import board
import busio

from devices.buzzer import Buzzer
from sensors.pmsa003i import PMSA003ISensor
from sensors.scd4x import SCD4xSensor
from config import *


def calculate_air_quality_index(data: Dict, thresholds: Dict):
    weights = {
        "co2": 0.40,
        "pm25": 0.30,
        "humidity": 0.15,
        "temperature": 0.15
    }

    aqi = 0
    max_aqi = 100
    danger_trigger = 70
    danger_zone = False

    for parameter, value in data.items():
        if parameter in thresholds:
            warning = thresholds[parameter].get("warning")
            danger = thresholds[parameter].get("danger")

            if value >= danger:
                danger_zone = True

            if value <= warning:
                aqi_contrib = 0
            elif value <= danger:
                aqi_contrib = (value - warning) / (danger - warning) * max_aqi
            else:
                aqi_contrib = max_aqi

            aqi += aqi_contrib * weights[parameter]

    if danger_zone:
        aqi = max(aqi, danger_trigger)

    aqi = min(aqi, max_aqi)

    return round(aqi)


async def send_alerts(cfg: Dict) -> None:
    previous_alerts = {
        "temperature": "normal",
        "humidity": "normal",
        "co2": "normal",
        "pm25": "normal",
    }
    buzzer = Buzzer(18)

    while True:
        for key, value in shared_state.items():
            if (value > CURRENT_THRESHOLDS[key]['danger']) and (previous_alerts[key] != "danger"):
                previous_alerts[key] = 'danger'
                PUBNUB_CLIENT.send_alert(title=f"{key} alert",
                                         message=f"{key} in a dangerous level: {value}",
                                         status='high',
                                         value=value
                                         )
                buzzer.play_alert(5)
            elif (value > CURRENT_THRESHOLDS[key]['warning']) and (
                    previous_alerts[key] not in ['warning', 'danger']):
                previous_alerts[key] = 'warning'
                PUBNUB_CLIENT.send_alert(title=f"{key} alert",
                                         message=f"{key} in a warning level: {value}",
                                         status='warning',
                                         value=value
                                         )
            elif value < CURRENT_THRESHOLDS[key]['warning'] and (previous_alerts[key] != "normal"):
                previous_alerts[key] = 'normal'

        try:
            await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            break


async def read_telemetry_data() -> None:
    I2C = busio.I2C(board.SCL, board.SDA, frequency=100000)
    pm_sensor = PMSA003ISensor(I2C, reset_pin=None)
    scd_sensor = SCD4xSensor(I2C)

    while True:
        scd_data = scd_sensor.read_telemetry()
        pm_data = pm_sensor.read_telemetry()

        shared_state["temperature"] = round(scd_data["temperature"])
        shared_state["co2"] = scd_data["co2"]
        shared_state["humidity"] = round(scd_data["humidity"])
        shared_state["pm25"] = pm_data["p_25"]

        try:
            await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            break


async def send_telemetry_update(cfg: Dict) -> None:
    while True:
        shared_state["aqi"] = calculate_air_quality_index(shared_state, CURRENT_THRESHOLDS)
        PUBNUB_CLIENT.send_telemetry(**shared_state)

        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            break

def handle_pubnub_message(message: Dict) -> None:
    request_type = message.get("request_type", None)

    if request_type == "change_thresholds_level":
        thresholds = message.get("thresholds")
        if thresholds:
            logger.info(f"Received threshold update: {thresholds}")
            cfg = load_config(CONFIG_PATH)
            cfg['thresholds'] = thresholds
            save_config(CONFIG_PATH, cfg)
            CURRENT_THRESHOLDS.update(thresholds)
            logger.info(f"Updated thresholds in config: {thresholds}")


async def listen_pubnub_messages() -> None:
    try:
        PUBNUB_CLIENT.subscribe(message_handler=handle_pubnub_message)
        logger.info("Subscribed to PubNub channel for threshold updates")

        while True:
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
    except Exception as e:
        logger.error(f"Error in PubNub listener thread: {e}")
    finally:
        PUBNUB_CLIENT.unsubscribe()
        logger.info("Unsubscribed from PubNub channel")