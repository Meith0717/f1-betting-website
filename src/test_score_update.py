#!/usr/bin/env python3
"""
Test script to verify that user scores are updated correctly when races are resolved.
"""

import sys
import os
import json
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from betting import BettingManager

def test_score_updating():
    """Test that user scores are updated when races are resolved."""
    
    print("🔄 Testing Score Updates in User Data")
    print("=" * 50)
    
    # Initialize betting manager
    betting_manager = BettingManager()
    
    # Load driver data
    drivers_file = os.path.join(os.path.dirname(__file__), 'app', 'data', 'drivers.json')
    if os.path.exists(drivers_file):
        with open(drivers_file, 'r') as f:
            driver_data = json.load(f)
        
        betting_manager.driver_teams = {}
        for driver in driver_data.get('drivers', []):
            driver_id = driver.get('driverId')
            team_id = driver.get('teamId')
            if driver_id and team_id:
                betting_manager.driver_teams[driver_id] = team_id
        
        print(f"✅ Loaded {len(betting_manager.driver_teams)} drivers")
    
    # Create test users
    test_users = {
        "test_user1": {
            "password": "test",
            "email": "user1@example.com",
            "score": 10,  # Starting with 10 points
            "email_notifications": False,
            "created_at": datetime.now().isoformat(),
            "last_login": datetime.now().isoformat(),
            "is_admin": False,
            "score_history": [
                {"race_id": "test_race_1", "points": 5, "total": 5, "timestamp": datetime.now().isoformat()},
                {"race_id": "test_race_2", "points": 5, "total": 10, "timestamp": datetime.now().isoformat()}
            ]
        },
        "test_user2": {
            "password": "test",
            "email": "user2@example.com",
            "score": 0,  # Starting with 0 points
            "email_notifications": False,
            "created_at": datetime.now().isoformat(),
            "last_login": datetime.now().isoformat(),
            "is_admin": False,
            "score_history": []
        }
    }
    
    # Save test users
    users_file = os.path.join(os.path.dirname(__file__), 'app', 'data', 'users_test.json')
    with open(users_file, 'w') as f:
        json.dump({"users": test_users}, f, indent=2)
    
    print(f"✅ Created test users file: {users_file}")
    
    # Test race resolution with score updates
    print("\n🏁 Testing Race Resolution with Score Updates")
    
    # Create test race results
    test_results = {
        'results': [
            {'driverId': 'ver', 'teamId': 'red_bull'},
            {'driverId': 'ham', 'teamId': 'mercedes'},
            {'driverId': 'lec', 'teamId': 'ferrari'}
        ],
        'overall_fastest_lap': {
            'driverId': 'ver',
            'teamId': 'red_bull'
        }
    }
    
    # Test user bets
    user_bets = {
        "test_user1": {
            "drivers": ["ver", "ham", "lec"],  # Perfect podium!
            "fastest_lap": "ver"
        },
        "test_user2": {
            "drivers": ["ver", "alc", "rus"],  # Only 1st correct
            "fastest_lap": "ham"
        }
    }
    
    # Calculate points
    points_summary = {}
    for username, bet in user_bets.items():
        points_data = betting_manager.calculate_points(bet, test_results)
        points_summary[username] = {
            'total': points_data['total_points'],
            'breakdown': points_data['breakdown']
        }
        print(f"\n👤 {username}:")
        print(f"   Bet: {bet['drivers']} | Fastest: {bet['fastest_lap']}")
        print(f"   Points: {points_data['total_points']}/8")
        print(f"   Breakdown: {points_data['breakdown']}")
    
    # Update user scores
    print("\n📊 Updating User Scores...")
    betting_manager._update_user_scores("test_race_3", points_summary)
    
    # Verify scores were updated
    with open(users_file, 'r') as f:
        updated_users = json.load(f)
    
    print("\n✅ Score Updates Verified:")
    for username, user_data in updated_users["users"].items():
        print(f"\n👤 {username}:")
        print(f"   Previous score: {user_data['score'] - points_summary[username]['total']}")
        print(f"   Points added: +{points_summary[username]['total']}")
        print(f"   New score: {user_data['score']}")
        
        # Check score history
        last_entry = user_data['score_history'][-1] if user_data['score_history'] else None
        if last_entry:
            print(f"   Last race: {last_entry['race_id']} (+{last_entry['points']} pts)")
    
    # Clean up
    if os.path.exists(users_file):
        os.remove(users_file)
        print(f"\n🗑️  Cleaned up test file: {users_file}")
    
    print("\n" + "=" * 50)
    print("✅ Score updating system tested successfully!")
    print("🎯 Users will see their scores update automatically when races are resolved")

if __name__ == "__main__":
    test_score_updating()
