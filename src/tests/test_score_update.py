#!/usr/bin/env python3
"""
Test that user scores are updated correctly when races are resolved.
Uses ResolutionService and UserService directly.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services import bet_service, resolution_service, user_service


def test_score_updating(app):
    """Test that user scores are updated when races are resolved."""
    with app.app_context():
        # Set up driver teams
        resolution_service.set_driver_teams({
            "ver": "red_bull",
            "ham": "mercedes",
            "lec": "ferrari",
            "alc": "aston_martin",
            "rus": "mercedes",
            "sai": "ferrari",
        })

        # Clear and create test users
        user_service.save_all({"users": {}})
        user_service.create("test_user1", "test", is_admin=False)
        user_service.create("test_user2", "test", is_admin=False)
        user_service.update("test_user1", score=10)

        # Place bets
        bet_service.save_all({"race_bets": {}, "metadata": {}})
        bet_service.place_bet(
            "test_user1", "test_race_3",
            ["ver", "ham", "lec"], "ver",  # perfect
        )
        bet_service.place_bet(
            "test_user2", "test_race_3",
            ["ver", "alc", "rus"], "ham",  # partial
        )

        # Resolve the race
        summary = resolution_service.resolve_with_results(
            "test_race_3", ["ver", "ham", "lec"], "ver"
        )

        # Verify points
        assert summary["test_user1"]["total_points"] == 8
        assert summary["test_user2"]["total_points"] == 2

        # Verify user scores were updated
        u1 = user_service.get("test_user1")
        u2 = user_service.get("test_user2")
        assert u1["score"] == 18  # 10 + 8
        assert u2["score"] == 2   # 0 + 2

        # Verify score history
        assert len(u1["score_history"]) == 1
        assert u1["score_history"][0]["race_id"] == "test_race_3"
        assert u1["score_history"][0]["points"] == 8

        # Clean up
        user_service.save_all({"users": {}})
        bet_service.save_all({"race_bets": {}, "metadata": {}})


if __name__ == "__main__":
    from app import create_app
    app = create_app()
    test_score_updating(app)
    print("Score update test passed!")
