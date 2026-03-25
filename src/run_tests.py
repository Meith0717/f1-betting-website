#!/usr/bin/env python3
"""
Test runner for F1 Betting Application.

This script runs all tests and provides a comprehensive test report.
"""

import subprocess
import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_tests():
    """Run all tests and return results."""
    print("🏎️  F1 Betting Application Test Suite")
    print("=" * 50)

    # Run pytest tests
    print("🧪 Running pytest tests...")
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_betting_system.py",
                "-v",
                "--tb=short",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        if result.returncode == 0:
            print("✅ All pytest tests passed!")
        else:
            print("❌ Some pytest tests failed!")

    except Exception as e:
        print(f"❌ Error running pytest tests: {e}")
        return False

    # Run legacy tests
    print("\n🔄 Running legacy tests...")

    legacy_tests = [
        ("test_scoring.py", "Scoring System Test"),
        ("test_integration.py", "Integration Test"),
    ]

    legacy_passed = 0
    legacy_total = len(legacy_tests)

    for test_file, test_name in legacy_tests:
        try:
            print(f"📋 Running {test_name}...")
            # Set PYTHONPATH to include the src directory
            env = os.environ.copy()
            env["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__))
            result = subprocess.run(
                [sys.executable, test_file],
                capture_output=True,
                text=True,
                cwd="tests",
                env=env,
            )

            if result.returncode == 0:
                print(f"✅ {test_name} passed!")
                legacy_passed += 1
            else:
                print(f"❌ {test_name} failed!")
                print("STDOUT:", result.stdout[-500:])  # Last 500 chars
                if result.stderr:
                    print("STDERR:", result.stderr[-500:])  # Last 500 chars

        except Exception as e:
            print(f"❌ Error running {test_name}: {e}")

    print(f"\n📊 Legacy Tests: {legacy_passed}/{legacy_total} passed")

    # Summary
    print("\n" + "=" * 50)
    print("🏁 Test Suite Complete!")

    if legacy_passed == legacy_total:
        print("🎉 All tests passed! The application is ready for deployment.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the output above.")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
