#!/usr/bin/env python3

"""Quick connect script pre-filled from my-vector.md."""

import configparser
from pathlib import Path
import sys

import anki_vector
from anki_vector.connection import ControlPriorityLevel

VECTOR_NAME = "Vector-S7Y5"
VECTOR_IP = "192.168.1.186"
VECTOR_SERIAL = "0dd1cabe"


def read_local_auth(serial):
    config_path = Path.home() / ".anki_vector" / "sdk_config.ini"
    parser = configparser.ConfigParser(strict=False)
    parser.read(str(config_path))
    if serial not in parser:
        raise RuntimeError(
            "Missing {} section in {}. Run configure first.".format(serial, config_path)
        )
    section = parser[serial]
    cert = section.get("cert")
    guid = section.get("guid")
    if not cert or not guid:
        raise RuntimeError("Config section is missing cert or guid")
    return cert, guid


def main():
    serial = VECTOR_SERIAL.lower()
    cert, guid = read_local_auth(serial)

    robot = anki_vector.Robot(
        serial=serial,
        name=VECTOR_NAME,
        ip=VECTOR_IP,
        config={"cert": cert, "guid": guid},
        default_logging=False,
        behavior_control_level=ControlPriorityLevel.DEFAULT_PRIORITY,
    )

    try:
        robot.connect()
        print("Connected to {} at {}".format(VECTOR_NAME, VECTOR_IP))
        print("Status: on_charger={}, charging={}".format(
            robot.status.is_on_charger,
            robot.status.is_charging,
        ))
    finally:
        try:
            robot.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Quick test failed: {}".format(exc))
        sys.exit(1)
