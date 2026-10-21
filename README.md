# ble_scan

Scan for nearby Bluetooth Low Energy (BLE) devices from the command line.

**Version:** 2026.10.21.1

## Features

- Lists nearby BLE devices sorted by signal strength (RSSI)
- Rough distance estimate in metres
- Vendor lookup from manufacturer data (Apple, Samsung, Google, Garmin, ...)
- Apple device-type hints (iPhone/Mac, AirPods, AirTag/Find My, iBeacon, ...)
- Recognizes common services (Battery, Heart Rate, HID, Eddystone, Fast Pair, ...)
- Live mode, signal filtering, JSON/CSV export

## Requirements

- Python 3.9+
- [bleak](https://github.com/hbldh/bleak): `pip install bleak`
- Works on macOS, Linux (BlueZ) and Windows 10+

## Usage

```bash
python3 ble_scan.py                  # 10 s scan, results table
python3 ble_scan.py -t 30            # scan for 30 s
python3 ble_scan.py --live           # print devices as they are discovered
python3 ble_scan.py --min-rssi -80   # hide weak/far devices
python3 ble_scan.py --json out.json  # save results as JSON
python3 ble_scan.py --csv out.csv    # save results as CSV
python3 ble_scan.py --version
```

| Option | Description |
|---|---|
| `-t`, `--timeout` | Scan duration in seconds (default 10) |
| `--live` | Print each new device as it is found |
| `--min-rssi` | Ignore devices weaker than this value in dBm |
| `--json FILE` | Save results to JSON |
| `--csv FILE` | Save results to CSV |
| `-v`, `--version` | Show version |

## Example output

```
 RSSI     ~m  Name                     Vendor               Type / Services                        Address
-------------------------------------------------------------------------------------------------------------
  -48    0.4  MacBook Pro              Apple                Nearby Info (iPhone/iPad/Mac/Watch)    1A2B...
  -71    5.6                           Apple                Find My / AirTag                       3C4D...
  -83   22.4  Forerunner 265           Garmin               Heart Rate                             5E6F...
```

## Notes

- **macOS permission:** the first run asks for Bluetooth access for Terminal (or your IDE). If no devices appear, enable it in *System Settings → Privacy & Security → Bluetooth*.
- **Addresses:** macOS hides real MAC addresses and shows a UUID unique to each Mac instead.
- **Duplicates:** phones, earbuds and trackers rotate random addresses every few minutes, so one device may appear more than once.
- **Distance** is a rough estimate. Walls, bodies and antenna orientation can change it a lot.
- Only BLE devices are detected. For classic Bluetooth, use `blueutil --inquiry` (macOS) or `bluetoothctl scan on` (Linux).
