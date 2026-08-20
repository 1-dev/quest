#!/usr/bin/env python3
"""
Generate unique number sets for Volunteer Sprint participants.

Numbers 1-21, each participant gets 1-5 random numbers, no repeats.

Usage:
    python3 generate_numbers.py PARTICIPANTS [--min 1] [--max 5] [--names]

Output:
    CSV file (Participant,Numbers) — ready to upload to Google Sheets "Numbers" tab.
    Use --names to enter participant names interactively.
"""

import argparse
import random
import sys
import csv

ALL_NUMBERS = list(range(1, 22))


def generate_sets(count, min_per_person=1, max_per_person=5):
    pool = ALL_NUMBERS.copy()
    random.shuffle(pool)

    total_needed = count * min_per_person
    if total_needed > len(pool):
        print(f"Ошибка: нужно {total_needed} номерков, доступно {len(pool)}")
        print(f"Максимум участников: {len(pool) // min_per_person}")
        sys.exit(1)

    sets = []
    idx = 0
    for i in range(count):
        remaining = count - i
        available = len(pool) - idx
        needed = remaining * min_per_person
        room = available - needed + min_per_person
        n = min(max_per_person, max(min_per_person, min(room, max_per_person)))
        n = min(n, len(pool) - idx)
        nums = sorted(pool[idx:idx + n])
        idx += n
        sets.append(nums)
    return sets


def main():
    parser = argparse.ArgumentParser(description="Generate unique number sets")
    parser.add_argument("participants", type=int, help="Number of participants")
    parser.add_argument("--min", type=int, default=1, help="Min numbers per person (default: 1)")
    parser.add_argument("--max", type=int, default=5, help="Max numbers per person (default: 5)")
    parser.add_argument("--names", action="store_true", help="Enter participant names interactively")
    args = parser.parse_args()

    sets = generate_sets(args.participants, args.min, args.max)

    names = []
    if args.names:
        print("Введи имена участников (enter = пропустить):")
        for i in range(args.participants):
            name = input(f"  {i + 1}. ").strip()
            names.append(name if name else f"Участник {i + 1}")
    else:
        names = [f"Участник {i + 1}" for i in range(args.participants)]

    # Print
    total_nums = sum(len(s) for s in sets)
    print(f"\nУчастников: {args.participants}")
    print(f"Номерков: {total_nums}/{len(ALL_NUMBERS)}")
    print("=" * 40)
    for name, nums in zip(names, sets):
        print(f"  {name}: {nums}")
    print("=" * 40)

    # Save CSV
    filename = f"numbers-{args.participants}p.csv"
    with open(filename, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Participant", "Numbers"])
        for name, nums in zip(names, sets):
            w.writerow([name, ", ".join(str(n) for n in nums)])
    print(f"\nСохранено: {filename}")
    print("Загрузи в Google Sheets → вкладка 'Numbers'")


if __name__ == "__main__":
    main()
