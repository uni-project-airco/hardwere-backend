import json
import logging
from pathlib import Path
from typing import Union, TypeAlias

from vendors.pubnub.client import PubNubClient

logging.basicConfig(
    filename="../logfile.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

JSON_DATA: TypeAlias = dict[str, Union[str, int, dict]]
shared_state: dict = {}


def load_config(path: Path) -> JSON_DATA:
    with open(path) as f:
        return json.load(f)


def save_config(path: Path, cfg: JSON_DATA) -> None:
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)


def update_pubnub_token_in_config(new_token: str) -> None:
    cfg = load_config(CONFIG_PATH)
    cfg["pubnub"]["access-token"] = new_token
    save_config(CONFIG_PATH, cfg)
    logger.info("Updated PubNub access token in config file")


CONFIG_PATH = Path(__file__).parent.parent / "config.json"
CONFIG = load_config(CONFIG_PATH)

PUBNUB_CLIENT = PubNubClient(
    sub_key=CONFIG["pubnub"]["subscribe-key"],
    pub_key=CONFIG["pubnub"]["publish-key"],
    sensor_id=CONFIG["sensor-id"],
    chanel_name=CONFIG["pubnub"]["channel-name"],
    access_token=CONFIG["pubnub"]["access-token"],
    server_url=CONFIG["server-url"],
    certification_string=CONFIG["certificate-string"],
    config_update_callback=update_pubnub_token_in_config,
)
CURRENT_THRESHOLDS = {}
