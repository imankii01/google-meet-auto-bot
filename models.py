from pymongo import MongoClient
from config import Config

class MongoDB:
    def __init__(self):
        self.client = MongoClient(Config.MONGO_URI)
        self.db = self.client[Config.DB_NAME]

    def save_bot_status(self, bot_id, status, meet_link):
        """Save bot's current status to the database."""
        bot_status = {
            "bot_id": bot_id,
            "status": status,
            "meet_link": meet_link,
            "start_time": datetime.now(),
        }
        self.db.bot_status.insert_one(bot_status)

    def get_active_bots(self):
        """Get the list of active bots."""
        active_bots = self.db.bot_status.find({"status": "running"})
        return list(active_bots)

    def update_bot_status(self, bot_id, status):
        """Update the status of a running bot."""
        self.db.bot_status.update_one(
            {"bot_id": bot_id}, {"$set": {"status": status}}
        )

    def save_transcription(self, bot_id, transcription):
        """Save transcription to MongoDB."""
        self.db.transcriptions.insert_one({
            "bot_id": bot_id,
            "transcription": transcription,
            "timestamp": datetime.now()
        })

    def save_screenshot(self, bot_id, screenshot_data):
        """Save screenshot reference to MongoDB."""
        self.db.screenshots.insert_one({
            "bot_id": bot_id,
            "screenshot_data": screenshot_data,
            "timestamp": datetime.now()
        })
