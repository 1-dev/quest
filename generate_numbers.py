#!/usr/bin/env python3
"""
Generate unique number sets for Volunteer Sprint participants.

Numbers 1-21, each participant gets 1-5 random numbers, no repeats across participants.

Usage:
    python3 generate_numbers.py PARTICIPANTS [--min 1] [--max 5]

Example:
    python3 generate_numbers.py 10
    python3 generate_numbers.py 15 --min 2 --max 4
"""

import argparse
import random
import sys

ALL_NUMBERS = list(range(1, 22))


def generate_sets(participant_count, min_per_person=1, max_per_person=5):
    pool = ALL_NUMBERS.copy()
    random.shuffle(pool)

    total_needed_min = participant_count * min_per_person
    total_available = len(pool)

    if total_needed_min > total_available:
        print(f"Ошибка: нужно минимум {total_needed_min} номерков, но доступно только {total_available}")
        print(f"Максимум участников при {min_per_person} номерках: {total_available // min_per_person}")
        sys.exit(1)

    sets = []
    pool_idx = 0

    for i in range(participant_count):
        remaining_participants = participant_count - i
        remaining_numbers = len(pool) - pool_idx
        needed = remaining_participants * min_per_person
        available_for_this = remaining_numbers - needed + min_per_person
        count = min(max_per_person, max(min_per_person, min(available_for_this, max_per_person)))
        count = min(count, len(pool) - pool_idx)

        nums = sorted(pool[pool_idx:pool_idx + count])
        pool_idx += count
        sets.append(nums)

    return sets


def main():
    parser = argparse.ArgumentParser(description="Generate unique number sets")
    parser.add_argument("participants", type=int, help="Number of participants")
    parser.add_argument("--min", type=int, default=1, help="Min numbers per person (default: 1)")
    parser.add_argument("--max", type=int, default=5, help="Max numbers per person (default: 5)")
    args = parser.parse_args()

    sets = generate_sets(args.participants, args.min, args.max)

    print(f"Участников: {args.participants}")
    print(f"Номерков на человека: {args.min}-{args.max}")
    print(f"Всего номерков: {sum(len(s) for s in sets)}/{len(ALL_NUMBERS)}")
    print()
    print("=" * 40)

    for i, nums in enumerate(sets, 1):
        nums_str = ", ".join(str(n) for n in nums)
        print(f"  Участник {i:2d}: [{nums_str}]")

    print("=" * 40)
    print()

    # Also save as CSV
    filename = f"numbers-{args.participants}p.csv"
    with open(filename, "w") as f:
        f.write("Участник,Номерки\n")
        for i, nums in enumerate(sets, 1):
            f.write(f'{i},"{", ".join(str(n) for n in nums)}"\n')
    print(f"Сохранено в {filename}")


if __name__ == "__main__":
    main()
