# Vector - Python SDK

This is a fork of the fork of the original Anki Vector Python SDK. *After gettng my own Vector long after Anki stopped
caring for it, I used AI to restore as much functionality as possible while staing compleatly cloud free. This fork uses `wire-pod` to communicate with the robot.* Thank you to the `ikkez` that made the first fork. This is fully unofficial and mostly just for my own amusement.

![Vector](docs/source/images/vector-sdk-alpha.jpg)

Learn more about Vector: https://www.anki.com/en-us/vector

Learn more about how Vector works: [Vector Bible](https://github.com/GooeyChickenman/victor/blob/master/documentation/Vector-TRM.pdf)

SDK documentation: https://vector.ikkez.de/

Forums: https://forums.anki.com/

Discord: https://discord.gg/ue6v2Z


## Getting Started

You can follow steps [here](https://developer.anki.com/vector/docs/index.html) to set up your Vector robot with the SDK.

To install his SDK fork run:

```
pip uninstall anki_vector
pip install ikkez_vector
```

Upgrade with 
```
pip install ikkez_vector --upgrade
```

## Local / Wire-Pod Setup (No Anki Cloud)

This fork is configured for local usage without Anki cloud.

Run local setup (GUID is auto-read from Wire-Pod bot info):

```bash
python -m anki_vector.configure \
	--serial <serial> \
	--name <Vector-XXXX> \
	--ip <robot_ip> \
	--wirepod-root <path_to_wire-pod>
```

If auto-detection fails, provide exact Wire-Pod paths:

```bash
python -m anki_vector.configure \
	--serial <serial> \
	--name <Vector-XXXX> \
	--ip <robot_ip> \
	--wirepod-bot-info <path_to_botSdkInfo.json> \
	--wirepod-session-certs <path_to_session-certs>
```

If runtime files are not local on this machine, use Wire-Pod API fallback:

```bash
python -m anki_vector.configure \
	--serial <serial> \
	--name <Vector-XXXX> \
	--ip <robot_ip> \
	--wirepod-host <wirepod_host> \
	--wirepod-port 8080
```

The configure command reads:

- `http://<wirepod_host>:8080/api-sdk/get_sdk_info` for GUID info
- `http://<wirepod_host>:8080/session-certs/<serial>` for cert data

You can override GUID/cert manually if needed:

```bash
python -m anki_vector.configure \
	--serial <serial> \
	--name <Vector-XXXX> \
	--ip <robot_ip> \
	--cert <path_to_robot_cert.pem> \
	--guid <robot_guid>
```

Where GUID is stored in Wire-Pod:

- `chipper/jdocs/botSdkInfo.json`
- field `robots[].guid` for per-robot token
- fallback field `global_guid`

Where cert is stored in Wire-Pod:

- `chipper/session-certs/<serial>`

If no cert is found in Wire-Pod storage, configure fetches the cert directly from `robot_ip:443`.

After setup, run a quick connectivity check:

```bash
python scripts/test_local_connection.py --serial <serial>
```

### Changelog

To see all changes and updates being made to the SDK, please go to [Releases](https://github.com/ikkez/vector-python-sdk/releases)

## Privacy Policy and Terms and Conditions

Use of Vector and the Vector SDK is subject to Anki's [Privacy Policy](https://www.anki.com/en-us/company/privacy) and [Terms and Conditions](https://www.anki.com/en-us/company/terms-and-conditions).
