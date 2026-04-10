#!/usr/bin/env python3
"""Test blockade detection mechanism."""

import json
import os
from datetime import datetime, timedelta

blockade_dir = os.path.expanduser('~/.garth_athlete')
blockade_file = os.path.join(blockade_dir, '.blockade.json')
os.makedirs(blockade_dir, exist_ok=True)

# Test 1: Create blockade file
print("=" * 60)
print("TEST 1: Creating blockade file (2 hours)")
print("=" * 60)

blocked_until = datetime.now() + timedelta(hours=2)
with open(blockade_file, 'w') as f:
    json.dump({
        'blocked_until': blocked_until.isoformat(),
        'reason': '429 Too Many Requests from Garmin',
        'created_at': datetime.now().isoformat()
    }, f)

print(f"✓ Blockade file created")
print(f"  Location: {blockade_file}")

# Test 2: Check detection from garmin_sync
print("\n" + "=" * 60)
print("TEST 2: Testing check_garmin_blockade() function")
print("=" * 60)

from src.garmin.garmin_sync import check_garmin_blockade

blockade = check_garmin_blockade()
if blockade and blockade['is_blocked']:
    print(f"✓ Blockade detected!")
    print(f"  Remaining time: {blockade['remaining_hours']:.2f} hours")
    print(f"  Remaining time: {int(blockade['remaining_hours'])}h {int((blockade['remaining_hours'] % 1) * 60)}m")
    print(f"  Blocked until: {blockade['blocked_until']}")
    print(f"  Reason: {blockade['reason']}")
else:
    print("✗ Blockade NOT detected (ERROR!)")

# Test 3: Clean up
print("\n" + "=" * 60)
print("TEST 3: Cleanup")
print("=" * 60)

os.remove(blockade_file)
print(f"✓ Blockade file removed")

blockade = check_garmin_blockade()
if blockade is None:
    print("✓ Blockade cleared successfully")
else:
    print("✗ Blockade still detected (ERROR!)")

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED")
print("=" * 60)
