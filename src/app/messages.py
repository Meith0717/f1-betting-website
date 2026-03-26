import os
import json
from datetime import datetime


class MessageManager:
    """Simple message storage using a text file."""

    def __init__(self, message_file="messages.txt"):
        self.message_file = message_file or os.path.join(
            os.path.dirname(__file__), "data", "messages.txt"
        )

    def add_message(self, username, comment):
        """Add a comment to the file."""
        comment_data = {
            "username": username,
            "comment": comment,
            "timestamp": datetime.now().isoformat(),
        }

        # Read existing messages
        messages = []
        if os.path.exists(self.message_file):
            with open(self.message_file, "r") as f:
                try:
                    messages = json.load(f)
                except:
                    messages = []

        # Add new message
        messages.append(comment_data)

        # Keep only last 20 messages
        if len(messages) > 20:
            messages = messages[-20:]

        # Save
        with open(self.message_file, "w") as f:
            json.dump(messages, f, indent=2)

        return True

    def get_messages(self):
        """Get all messages, newest first."""
        if not os.path.exists(self.message_file):
            return []

        with open(self.message_file, "r") as f:
            try:
                messages = json.load(f)
                # Return newest first (reverse chronological order)
                return messages[::-1]
            except:
                return []


# Message manager instance - create with explicit path to ensure correct location
message_manager = MessageManager(os.path.join(os.path.dirname(__file__), "data", "messages.txt"))
