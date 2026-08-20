#!/usr/bin/env python3
"""
QR Code generator for Volunteer Sprint Quest (v3 — token-gated).

Physical QR codes link to start.html?cp=N which issues a session token.
No backend needed — tokens are generated client-side from a session salt.

Usage:
    python3 generate_qr.py [--base-url URL] [--copies N]

Requires: qrcode[pil]  (pip install "qrcode[pil]")
"""

import argparse
import os
import sys

try:
    import qrcode
    from qrcode.image.styledpil import StyledPilImage
    from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
except ImportError:
    print("Error: qrcode library not installed.")
    print('Install with: pip install "qrcode[pil]"')
    sys.exit(1)


DEFAULT_BASE_URL = "https://yourschool21.github.io/volunteer-sprint/"

CHECKPOINTS = [
    {"id": 0, "label": "01-norminnet",  "title": "Норминнет-Детектив",  "loc": "ARM в кластере Lepton, ряд C"},
    {"id": 1, "label": "02-silence",    "title": "Комната Тишины",      "loc": "Малая переговорка для уединённых бесед"},
    {"id": 2, "label": "03-caffeine",   "title": "Зона Кофеина",        "loc": "Столовая ИЛИ автомат с кофе"},
    {"id": 3, "label": "04-black-hole", "title": "Чёрная Дыра",         "loc": "Библиотека — самая далёкая точка"},
    {"id": 4, "label": "05-heart",      "title": "Сердце Кампуса",      "loc": "Логотип School 21 у входа"},
    {"id": 5, "label": "06-pullups",    "title": "Турникет",            "loc": "Закуток с турниками по пути в библиотеку"},
    {"id": 6, "label": "07-arcade",     "title": "Аркада",              "loc": "Игровая зона с PSP"},
    {"id": 7, "label": "08-boson",      "title": "Скрытый Монитор",     "loc": "Кластер Boson — за лестницей"},
]


def generate_qr(url, output_path, size=10):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=size,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
    )
    img.save(output_path)


def main():
    parser = argparse.ArgumentParser(description="Generate QR codes for Volunteer Sprint v3")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL,
                        help=f"Base URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--output-dir", default="qr-codes",
                        help="Output directory (default: qr-codes/)")
    parser.add_argument("--copies", type=int, default=4,
                        help="QR copies per checkpoint (default: 4)")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    base = args.base_url.rstrip("/")

    print("⚡ Volunteer Sprint QR Generator v3 (token-gated)")
    print(f"   Base URL : {base}")
    print(f"   Output   : {args.output_dir}/")
    print(f"   Copies   : {args.copies} per checkpoint")
    print()
    print("  QR → start.html?cp=N → issues session token → run.html?t=TOKEN")
    print()

    total = 0

    for cp in CHECKPOINTS:
        url = f"{base}/start.html?cp={cp['id']}"
        for copy_num in range(1, args.copies + 1):
            fname = f"{args.output_dir}/{cp['label']}-copy{copy_num}.png"
            generate_qr(url, fname)
            print(f"  ✓ {fname}")
            print(f"    loc: {cp['loc']}")
            print(f"    url: {url}")
            total += 1
        print()

    print(f"🎉 Generated {total} QR codes in '{args.output_dir}/'")
    print()
    print("Deployment:")
    print("  1. Deploy HTML to GitHub Pages")
    print(f"  2. Re-run with --base-url https://<user>.github.io/<repo>/")
    print("  3. Print QRs: place 3-4 copies at each physical location")
    print("  4. Flow: scan QR → start.html issues token → run.html validates")


if __name__ == "__main__":
    main()
