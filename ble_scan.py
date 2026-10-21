#!/usr/bin/env python3
"""
ble_scan.py - Scan for nearby Bluetooth Low Energy (BLE) devices.

Version: 2026.10.21.1

Requirements:
    pip install bleak

Usage:
    python3 ble_scan.py                 # 10 s scan, table sorted by signal strength
    python3 ble_scan.py -t 30           # 30 s scan
    python3 ble_scan.py --live          # print devices as they are discovered
    python3 ble_scan.py --json out.json # also save results as JSON
    python3 ble_scan.py --csv out.csv   # also save results as CSV
    python3 ble_scan.py --min-rssi -80  # hide weak/far devices

macOS notes:
    - The first run triggers a Bluetooth permission prompt for Terminal (or your
      IDE). If nothing is found, check System Settings > Privacy & Security >
      Bluetooth and enable it for the app running the script.
    - macOS hides real MAC addresses; devices are identified by a per-Mac UUID.
    - Many devices (iPhones, AirPods, etc.) rotate random addresses every few
      minutes, so the same physical device may show up more than once.
"""

import argparse
import asyncio
import csv
import json
import sys
import time

__version__ = "2026.10.21.1"

try:
    from bleak import BleakScanner
except ImportError:
    sys.exit("bleak is not installed. Run:  pip install bleak")

# Bluetooth SIG company identifiers (subset)
COMPANY_IDS = {
    0x0006: "Microsoft",
    0x000D: "Texas Instruments",
    0x000F: "Broadcom",
    0x004C: "Apple",
    0x0059: "Nordic Semiconductor",
    0x0075: "Samsung",
    0x0087: "Garmin",
    0x00E0: "Google",
    0x0131: "Cypress Semiconductor",
    0x0157: "Huami (Amazfit)",
    0x0171: "Amazon",
    0x02E5: "Espressif",
    0x038F: "Xiaomi",
    0x0499: "Ruuvi Innovations",
}

# Apple "Continuity" message types (first byte of Apple manufacturer data)
APPLE_TYPES = {
    0x02: "iBeacon",
    0x05: "AirDrop",
    0x07: "AirPods/Beats",
    0x09: "AirPlay target",
    0x0C: "Handoff",
    0x0D: "Wi-Fi settings",
    0x0F: "Nearby Action",
    0x10: "Nearby Info (iPhone/iPad/Mac/Watch)",
    0x12: "Find My / AirTag",
}

# Common 16-bit GATT service UUIDs
SERVICES = {
    "180a": "Device Info",
    "180d": "Heart Rate",
    "180f": "Battery",
    "1812": "HID (keyboard/mouse)",
    "1816": "Cycling Speed/Cadence",
    "1818": "Cycling Power",
    "181a": "Environmental Sensing",
    "fd6f": "Exposure Notification",
    "fe2c": "Google Fast Pair",
    "fe9f": "Google",
    "feaa": "Eddystone beacon",
}


def short_uuid(uuid: str) -> str:
    """Return the 16-bit form of a standard Bluetooth base UUID, else the full UUID."""
    u = uuid.lower()
    if u.endswith("-0000-1000-8000-00805f9b34fb") and u.startswith("0000"):
        return u[4:8]
    return u


def describe_services(uuids):
    out = []
    for u in uuids or []:
        s = short_uuid(u)
        out.append(SERVICES.get(s, s))
    return out


def describe_vendor(manufacturer_data):
    """Return (vendor, hint) from advertisement manufacturer data."""
    if not manufacturer_data:
        return "", ""
    vendors, hints = [], []
    for cid, payload in manufacturer_data.items():
        vendors.append(COMPANY_IDS.get(cid, f"0x{cid:04X}"))
        if cid == 0x004C and payload:
            hints.append(APPLE_TYPES.get(payload[0], f"Apple type 0x{payload[0]:02X}"))
    return ", ".join(vendors), ", ".join(hints)


def estimate_distance(rssi, tx_power):
    """Very rough distance estimate in metres (log-distance path loss, n=2)."""
    if rssi is None:
        return None
    ref = tx_power if tx_power is not None else -59  # typical RSSI at 1 m
    return round(10 ** ((ref - rssi) / 20.0), 1)


def to_record(device, adv):
    vendor, hint = describe_vendor(adv.manufacturer_data)
    return {
        "address": device.address,
        "name": adv.local_name or device.name or "",
        "rssi": adv.rssi,
        "tx_power": adv.tx_power,
        "est_distance_m": estimate_distance(adv.rssi, adv.tx_power),
        "vendor": vendor,
        "hint": hint,
        "services": describe_services(adv.service_uuids),
        "manufacturer_data": {f"0x{k:04X}": v.hex() for k, v in adv.manufacturer_data.items()},
        "last_seen": time.strftime("%H:%M:%S"),
    }


def print_table(records):
    if not records:
        print("No devices found.")
        return
    hdr = f"{'RSSI':>5}  {'~m':>5}  {'Name':<24} {'Vendor':<20} {'Type / Services':<38} Address"
    print(hdr)
    print("-" * len(hdr))
    for r in records:
        dist = "" if r["est_distance_m"] is None else f"{r['est_distance_m']:.1f}"
        info = r["hint"] or ", ".join(r["services"])
        print(
            f"{r['rssi']:>5}  {dist:>5}  {r['name'][:24]:<24} {r['vendor'][:20]:<20} "
            f"{info[:38]:<38} {r['address']}"
        )
    print(f"\n{len(records)} device(s).")


async def scan(timeout, live, min_rssi):
    found = {}

    def on_detect(device, adv):
        if adv.rssi is not None and adv.rssi < min_rssi:
            return
        is_new = device.address not in found
        found[device.address] = to_record(device, adv)
        if live and is_new:
            r = found[device.address]
            label = r["name"] or r["hint"] or r["vendor"] or "(unknown)"
            print(f"[{r['last_seen']}] {r['rssi']:>4} dBm  {label:<40} {r['address']}")

    print(f"Scanning for {timeout:g} s ... (Ctrl+C to stop early)\n")
    scanner = BleakScanner(detection_callback=on_detect)
    await scanner.start()
    try:
        await asyncio.sleep(timeout)
    except asyncio.CancelledError:
        pass
    finally:
        await scanner.stop()

    return sorted(found.values(), key=lambda r: r["rssi"] if r["rssi"] is not None else -999, reverse=True)


def save_json(records, path):
    with open(path, "w") as f:
        json.dump(records, f, indent=2)
    print(f"Saved JSON: {path}")


def save_csv(records, path):
    fields = ["address", "name", "rssi", "tx_power", "est_distance_m", "vendor", "hint", "services", "last_seen"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in records:
            w.writerow({**r, "services": "; ".join(r["services"])})
    print(f"Saved CSV: {path}")


def main():
    p = argparse.ArgumentParser(description="Scan for nearby Bluetooth LE devices.")
    p.add_argument("-t", "--timeout", type=float, default=10.0, help="scan duration in seconds (default 10)")
    p.add_argument("--live", action="store_true", help="print devices as they are discovered")
    p.add_argument("--min-rssi", type=int, default=-127, help="ignore devices weaker than this (e.g. -80)")
    p.add_argument("--json", metavar="FILE", help="save results to a JSON file")
    p.add_argument("--csv", metavar="FILE", help="save results to a CSV file")
    p.add_argument("-v", "--version", action="version", version=__version__)
    args = p.parse_args()

    try:
        records = asyncio.run(scan(args.timeout, args.live, args.min_rssi))
    except KeyboardInterrupt:
        print("\nStopped.")
        return

    if args.live:
        print()
    print_table(records)
    if args.json:
        save_json(records, args.json)
    if args.csv:
        save_csv(records, args.csv)


if __name__ == "__main__":
    main()
