#!/usr/bin/env python3

"""
***Anki Vector Python SDK Local Setup (Wire-Pod)***

This script configures the Python SDK for local-only Vector usage.
It does not require Anki cloud endpoints.

Credential sources:
1) GUID from Wire-Pod bot info JSON (botSdkInfo.json)
2) Robot certificate from Wire-Pod session-certs/<serial> or directly from robot TLS

The script writes ~/.anki_vector/sdk_config.ini and stores the robot cert
in ~/.anki_vector.
"""

import argparse
import configparser
import json
import os
from pathlib import Path
import re
import ssl
import sys
from urllib.parse import urlparse
from urllib import error as urllib_error
from urllib import request as urllib_request

from cryptography import x509
from cryptography.hazmat.backends import default_backend

try:
    from termcolor import colored  # pylint: disable=import-error
except Exception:  # pylint: disable=broad-except
    def colored(text, color=None, on_color=None, attrs=None):  # pylint: disable=unused-argument
        return text


def get_serial(serial=None):
    if not serial:
        serial = os.environ.get("ANKI_ROBOT_SERIAL")
        if not serial:
            print("\n\nPlease find your robot serial number (ex. 00e20100) located on the underside of Vector, or accessible from Vector's debug screen.")
            serial = input("Enter robot serial number: ")
        else:
            print("Found robot serial number in environment variable '{}'".format(colored("ANKI_ROBOT_SERIAL", "green")))
    serial = serial.lower().strip()
    print("Using robot serial number: {}".format(colored(serial, "cyan")))
    return serial


def standardize_name(robot_name):
    if len(robot_name) == 4:
        robot_name = "Vector-{}".format(robot_name.upper())
    if re.match("[Vv]ector.[A-Za-z0-9]{4}", robot_name):
        robot_name = "V{}-{}".format(robot_name[1:-5], robot_name[-4:].upper())
    if re.match("Vector-[A-Z0-9]{4}", robot_name):
        return robot_name
    print(colored(" ERROR", "red"))
    sys.exit("Invalid robot name. Please match the format exactly. Example: Vector-A1B2")


def get_name_and_ip(robot_name=None, ip=None):
    if not robot_name:
        robot_name = os.environ.get("VECTOR_ROBOT_NAME")
        if not robot_name:
            print("\n\nFind your robot name (ex. Vector-A1B2) by placing Vector on the charger and double-clicking Vector's backpack button.")
            robot_name = input("Enter robot name: ")
        else:
            print("Found robot name in environment variable '{}'".format(colored("VECTOR_ROBOT_NAME", "green")))
    robot_name = standardize_name(robot_name)
    print("Using robot name: {}".format(colored(robot_name, "cyan")))

    if not ip:
        ip = os.environ.get("ANKI_ROBOT_HOST")
        if not ip:
            print("\n\nFind your robot ip address (ex. 192.168.42.42) by placing Vector on the charger, double-clicking Vector's backpack button, then raising and lowering his arms.")
            ip = input("Enter robot ip: ")
        else:
            print("Found robot ip address in environment variable '{}'".format(colored("ANKI_ROBOT_HOST", "green")))
    ip = ip.strip()
    print("Using IP: {}".format(colored(ip, "cyan")))
    return robot_name, ip


def _candidate_wirepod_bot_info_paths(wirepod_root=None):
    candidates = []
    env_bot_info = os.environ.get("VECTOR_WIREPOD_BOT_INFO")
    if env_bot_info:
        candidates.append(Path(os.path.expanduser(env_bot_info)))

    env_wirepod_root = os.environ.get("VECTOR_WIREPOD_ROOT")
    for root in [wirepod_root, env_wirepod_root, "/private/tmp/wire-pod", "~/wire-pod", "~/.config/wire-pod", "/var/lib/wire-pod"]:
        if not root:
            continue
        expanded = Path(os.path.expanduser(root))
        candidates.append(expanded / "chipper" / "jdocs" / "botSdkInfo.json")
        candidates.append(expanded / "jdocs" / "botSdkInfo.json")

    # Stable path used by the active workspace attachment in this session.
    candidates.append(Path("/private/tmp/wire-pod/chipper/jdocs/botSdkInfo.json"))

    ordered = []
    seen = set()
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(path)
    return ordered


def find_wirepod_bot_info(bot_info_file=None, wirepod_root=None):
    if bot_info_file:
        path = Path(os.path.expanduser(bot_info_file))
        if not path.exists():
            sys.exit("Wire-Pod bot info file does not exist: {}".format(path))
        return path

    for path in _candidate_wirepod_bot_info_paths(wirepod_root):
        if path.exists():
            return path
    return None


def read_guid_from_wirepod(serial, bot_info_path):
    with open(bot_info_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    global_guid = (data.get("global_guid") or "").strip()
    robots = data.get("robots") or []

    for robot in robots:
        robot_esn = (robot.get("esn") or "").strip().lower()
        if robot_esn != serial:
            continue
        robot_guid = (robot.get("guid") or "").strip()
        if robot_guid:
            return robot_guid, "robot"
        if global_guid:
            return global_guid, "global"
        return None, "missing"

    if global_guid:
        return global_guid, "global"
    return None, "missing"


def _http_get_bytes(url, timeout=5):
    req = urllib_request.Request(url, method="GET")
    with urllib_request.urlopen(req, timeout=timeout) as response:
        return response.read()


def normalize_wirepod_host(host):
    normalized = (host or "127.0.0.1").strip()
    if not normalized:
        return "127.0.0.1"
    parsed = urlparse(normalized)
    if parsed.scheme:
        normalized = parsed.netloc or parsed.path
    return normalized.strip("/")


def read_bot_info_from_wirepod_api(wirepod_host, wirepod_port):
    url = "http://{}:{}/api-sdk/get_sdk_info".format(normalize_wirepod_host(wirepod_host), wirepod_port)
    try:
        payload = _http_get_bytes(url)
    except urllib_error.URLError:
        return None
    try:
        return json.loads(payload.decode("utf-8"))
    except Exception:  # pylint: disable=broad-except
        return None


def read_guid_from_wirepod_api(serial, bot_info_data):
    global_guid = (bot_info_data.get("global_guid") or "").strip()
    robots = bot_info_data.get("robots") or []
    for robot in robots:
        robot_esn = (robot.get("esn") or "").strip().lower()
        if robot_esn != serial:
            continue
        robot_guid = (robot.get("guid") or "").strip()
        if robot_guid:
            return robot_guid, "robot"
        if global_guid:
            return global_guid, "global"
        return None, "missing"
    if global_guid:
        return global_guid, "global"
    return None, "missing"


def _candidate_session_cert_files(serial, bot_info_path=None, session_certs_dir=None, wirepod_root=None):
    candidates = []
    if session_certs_dir:
        root = Path(os.path.expanduser(session_certs_dir))
        candidates.append(root / serial)
        candidates.append(root / serial.upper())

    if bot_info_path:
        # .../jdocs/botSdkInfo.json -> .../session-certs/<serial>
        session_root = bot_info_path.parent.parent / "session-certs"
        candidates.append(session_root / serial)
        candidates.append(session_root / serial.upper())

    roots = [wirepod_root, os.environ.get("VECTOR_WIREPOD_ROOT"), "/private/tmp/wire-pod", "~/wire-pod", "~/.config/wire-pod", "/var/lib/wire-pod"]
    for root in roots:
        if not root:
            continue
        expanded = Path(os.path.expanduser(root))
        candidates.append(expanded / "chipper" / "session-certs" / serial)
        candidates.append(expanded / "chipper" / "session-certs" / serial.upper())
        candidates.append(expanded / "session-certs" / serial)
        candidates.append(expanded / "session-certs" / serial.upper())

    ordered = []
    seen = set()
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(path)
    return ordered


def read_cert_from_session_store(serial, bot_info_path=None, session_certs_dir=None, wirepod_root=None):
    for candidate in _candidate_session_cert_files(serial, bot_info_path, session_certs_dir, wirepod_root):
        if candidate.exists() and candidate.is_file():
            with open(candidate, "rb") as cert_handle:
                return cert_handle.read(), str(candidate)
    return None, None


def read_cert_from_wirepod_api(serial, wirepod_host, wirepod_port):
    url = "http://{}:{}/session-certs/{}".format(normalize_wirepod_host(wirepod_host), wirepod_port, serial)
    try:
        payload = _http_get_bytes(url)
    except urllib_error.URLError:
        return None, None
    return payload, url


def read_cert_from_robot_tls(ip, port=443):
    pem = ssl.get_server_certificate((ip, port))
    return pem.encode("utf-8")


def save_cert(cert, name, serial, anki_dir):
    os.makedirs(str(anki_dir), exist_ok=True)
    cert_file = str(anki_dir / "{name}-{serial}.cert".format(name=name, serial=serial))
    print("Writing certificate file to '{}'...\n".format(colored(cert_file, "cyan")))
    with os.fdopen(os.open(cert_file, os.O_WRONLY | os.O_CREAT, 0o600), "wb") as handle:
        handle.write(cert)
    return cert_file


def validate_cert_name(cert_file, robot_name):
    with open(cert_file, "rb") as handle:
        cert_bytes = handle.read()
    cert = x509.load_pem_x509_certificate(cert_bytes, default_backend())
    for field in cert.subject:
        if "commonName" in str(field.oid):
            common_name = field.value
            if common_name != robot_name:
                print(colored(" ERROR", "red"))
                sys.exit(
                    "The name of the certificate ({}) does not match the name provided ({}).\nPlease verify the name and try again.".format(common_name, robot_name)
                )
            return


def write_config(serial, cert_file=None, ip=None, name=None, guid=None, clear=True):
    home = Path.home()
    config_file = str(home / ".anki_vector" / "sdk_config.ini")
    print("Writing config file to '{}'...".format(colored(config_file, "cyan")))

    config = configparser.ConfigParser(strict=False)
    try:
        config.read(config_file)
    except configparser.ParsingError:
        if os.path.exists(config_file):
            os.rename(config_file, config_file + "-error")

    if clear:
        config[serial] = {}
    if serial not in config:
        config[serial] = {}

    if cert_file:
        config[serial]["cert"] = cert_file
    if ip:
        config[serial]["ip"] = ip
    if name:
        config[serial]["name"] = name
    if guid:
        config[serial]["guid"] = str(guid)

    temp_file = config_file + "-temp"
    if os.path.exists(config_file):
        os.rename(config_file, temp_file)
    try:
        with os.fdopen(os.open(config_file, os.O_WRONLY | os.O_CREAT, 0o600), "w") as handle:
            config.write(handle)
    except Exception as exc:  # pylint: disable=broad-except
        if os.path.exists(temp_file):
            os.rename(temp_file, config_file)
        raise exc
    else:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def main():
    parser = argparse.ArgumentParser(
        description="Configure local Vector SDK access using Wire-Pod data (no Anki cloud).",
        epilog="This command writes ~/.anki_vector/sdk_config.ini for SDK usage.",
    )
    parser.add_argument("-i", "--ip", help="Robot IP address, e.g. 192.168.1.186")
    parser.add_argument("-n", "--name", help="Robot name, e.g. Vector-A1B2")
    parser.add_argument("-s", "--serial", help="Robot serial, e.g. 00e20100")
    parser.add_argument("-u", "--update", dest="new_ip", help="Update stored robot IP only")
    parser.add_argument("--guid", help="Explicit GUID override (usually not required)")
    parser.add_argument("--cert", help="Explicit cert PEM path override (usually not required)")
    parser.add_argument("--wirepod-root", help="Wire-Pod root directory, e.g. /path/to/wire-pod")
    parser.add_argument("--wirepod-bot-info", help="Path to Wire-Pod botSdkInfo.json")
    parser.add_argument("--wirepod-session-certs", help="Path to Wire-Pod session-certs directory")
    parser.add_argument("--wirepod-host", default="127.0.0.1", help="Wire-Pod web host for API fallback (default: 127.0.0.1)")
    parser.add_argument("--wirepod-port", default="8080", help="Wire-Pod web port for API fallback (default: 8080)")
    parser.add_argument("--skip-name-check", action="store_true", help="Skip cert common-name validation")
    args = parser.parse_args()

    if args.new_ip:
        serial = get_serial(args.serial)
        write_config(serial, ip=args.new_ip, clear=False)
        print(colored("\nIP Updated!", "green"))
        sys.exit(0)

    print(__doc__)

    valid = ["y", "Y", "yes", "YES"]
    proceed = input("Do you wish to proceed? (y/n) ")
    if proceed not in valid:
        sys.exit("Stopping...")

    name, ip = get_name_and_ip(args.name, args.ip)
    serial = get_serial(args.serial)

    bot_info_path = find_wirepod_bot_info(args.wirepod_bot_info, args.wirepod_root)
    bot_info_data = None
    if bot_info_path is not None:
        print("Using Wire-Pod bot info: {}".format(colored(str(bot_info_path), "cyan")))
    else:
        print(colored("Wire-Pod bot info file was not auto-detected. Trying Wire-Pod API fallback...", "yellow"))
        bot_info_data = read_bot_info_from_wirepod_api(args.wirepod_host, args.wirepod_port)
        if bot_info_data is not None:
            print("Loaded bot info from Wire-Pod API endpoint /api-sdk/get_sdk_info")

    guid = args.guid
    if not guid and bot_info_path is not None:
        guid, source = read_guid_from_wirepod(serial, bot_info_path)
        if guid:
            if source == "robot":
                print("Loaded robot GUID from Wire-Pod bot info.")
            else:
                print("Using Wire-Pod global GUID fallback.")

    if not guid and bot_info_data is not None:
        guid, source = read_guid_from_wirepod_api(serial, bot_info_data)
        if guid:
            if source == "robot":
                print("Loaded robot GUID from Wire-Pod API bot info.")
            else:
                print("Using Wire-Pod API global GUID fallback.")

    if not guid:
        sys.exit(
            "Unable to determine GUID. Provide --guid or configure --wirepod-bot-info / --wirepod-root so botSdkInfo.json can be read."
        )

    cert = None
    cert_source = None
    if args.cert:
        cert_path = Path(os.path.expanduser(args.cert))
        if not cert_path.exists():
            sys.exit("Cert file does not exist: {}".format(cert_path))
        with open(cert_path, "rb") as cert_handle:
            cert = cert_handle.read()
        cert_source = str(cert_path)
    else:
        cert, cert_source = read_cert_from_session_store(
            serial,
            bot_info_path=bot_info_path,
            session_certs_dir=args.wirepod_session_certs,
            wirepod_root=args.wirepod_root,
        )

    if cert is None:
        cert, cert_source = read_cert_from_wirepod_api(serial, args.wirepod_host, args.wirepod_port)

    if cert is None:
        print("Session cert not found in Wire-Pod store. Fetching cert from robot TLS endpoint...")
        cert = read_cert_from_robot_tls(ip)
        cert_source = "robot-tls:{}:443".format(ip)

    print("Using cert source: {}".format(colored(cert_source, "cyan")))

    home = Path.home()
    anki_dir = home / ".anki_vector"
    cert_file = save_cert(cert, name, serial, anki_dir)

    if not args.skip_name_check:
        validate_cert_name(cert_file, name)

    write_config(serial, cert_file=cert_file, ip=ip, name=name, guid=guid)
    print(colored("\nSUCCESS! Local SDK configuration written.", "green"))


if __name__ == "__main__":
    main()
