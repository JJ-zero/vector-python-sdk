#!/usr/bin/env python3

"""Quick connectivity check for local/Wire-Pod Vector SDK setups."""

import argparse
import configparser
import os
from pathlib import Path
import sys

import anki_vector
from anki_vector.connection import ControlPriorityLevel


def read_sdk_config(serial):
    config_path = Path.home() / ".anki_vector" / "sdk_config.ini"
    parser = configparser.ConfigParser(strict=False)
    parser.read(str(config_path))
    serial_key = serial.lower()
    if serial_key not in parser:
        raise RuntimeError("Serial '{}' not found in {}".format(serial, config_path))
    section = parser[serial_key]
    return {
        "name": section.get("name"),
        "ip": section.get("ip"),
        "cert": section.get("cert"),
        "guid": section.get("guid"),
    }


def main():
    parser = argparse.ArgumentParser(description="Validate local Vector SDK auth/connectivity")
    parser.add_argument("-s", "--serial", required=True, help="Vector serial (for sdk_config.ini lookup)")
    parser.add_argument("-n", "--name", help="Robot name override, e.g. Vector-A1B2")
    parser.add_argument("-i", "--ip", help="Robot IP override")
    parser.add_argument("--cert", help="Certificate file override")
    parser.add_argument("--guid", help="GUID override")
    args = parser.parse_args()

    values = read_sdk_config(args.serial)
    if args.name:
        values["name"] = args.name
    if args.ip:
        values["ip"] = args.ip
    if args.cert:
        values["cert"] = os.path.expanduser(args.cert)
    if args.guid:
        values["guid"] = args.guid

    missing = [key for key in ("name", "ip", "cert", "guid") if not values.get(key)]
    if missing:
        raise RuntimeError("Missing required configuration values: {}".format(", ".join(missing)))

    print("Connecting to {} at {}...".format(values["name"], values["ip"]))
    robot = anki_vector.Robot(
        serial=args.serial,
        ip=values["ip"],
        name=values["name"],
        config={"cert": values["cert"], "guid": values["guid"]},
        default_logging=False,
        behavior_control_level=ControlPriorityLevel.DEFAULT_PRIORITY,
    )
    try:
        robot.connect()
        print("Connected. Battery state: {}".format(robot.status.battery_state))
    finally:
        try:
            robot.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Connection check failed: {}".format(exc))
        sys.exit(1)
