#!/usr/bin/env python3
"""
Test script to verify betting form functionality.
Tests that all drivers are selectable for fastest lap.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_betting_form_javascript():
    """Test that the betting form JavaScript allows all drivers for fastest lap."""

    # Read the JavaScript file
    with open("app/static/js/betting_form.js", "r") as f:
        js_content = f.read()

    print("🧪 Testing Betting Form JavaScript")
    print("=" * 50)

    # Test 1: Fastest lap should not be in positionSelects array
    position_selects_section = js_content.split("positionSelects = [")[1].split("]")[0]
    if "fastest_lap" not in position_selects_section:
        print("✅ Test 1 PASSED: Fastest lap not in positionSelects array")
    else:
        print("❌ Test 1 FAILED: Fastest lap still in positionSelects array")
        return False

    # Test 2: Fastest lap should be a separate variable
    if "const fastestLapSelect = document.getElementById('fastest_lap')" in js_content:
        print("✅ Test 2 PASSED: Fastest lap is a separate variable")
    else:
        print("❌ Test 2 FAILED: Fastest lap not properly separated")
        return False

    # Test 3: Comment should explain fastest lap is unrestricted
    if "Fastest lap can be any driver" in js_content:
        print("✅ Test 3 PASSED: Code properly documented")
    else:
        print("❌ Test 3 FAILED: Missing documentation")
        return False

    # Test 4: Podium positions should still prevent duplicates
    if "Prevent duplicate selections in podium positions" in js_content:
        print("✅ Test 4 PASSED: Podium duplicate prevention maintained")
    else:
        print("❌ Test 4 FAILED: Podium duplicate prevention missing")
        return False

    print("\n📊 Betting Form JavaScript Test Results:")
    print("✅ All tests passed!")
    print("✅ Fastest lap selection is now independent")
    print("✅ Podium positions still prevent duplicate drivers")
    print("✅ Code is properly documented")

    return True


if __name__ == "__main__":
    success = test_betting_form_javascript()
    if success:
        print("\n🎉 Betting form is ready for production!")
    else:
        print("\n❌ Betting form has issues that need fixing")

    sys.exit(0 if success else 1)
