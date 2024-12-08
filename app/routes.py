import logging
from flask import Blueprint, jsonify, request, render_template
from .automation import GoogleMeetAutomation
from datetime import datetime

api = Blueprint("api", __name__)

logger = logging.getLogger(__name__)

@api.route("/join-meet", methods=["POST"])
def join_meet_endpoint():
    """
    API endpoint to join a Google Meet.
    """
    try:
        data = request.json
        meet_link = data.get("meet_link")
        meeting_duration = data.get("meeting_duration", 30)

        if not meet_link:
            return jsonify({"status": "error", "message": "Missing meet_link"}), 400

        automation = GoogleMeetAutomation()
        result = automation.join_meeting(meet_link, meeting_duration)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Endpoint error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api.route("/", methods=["GET"])
def root_health_check():
    """
    Root endpoint providing health check with both JSON and HTML responses.
    """
    health_data = {
        "status": "OK",
        "timestamp": datetime.now().isoformat(),
    }
    return render_template("health.html", health_data=health_data)
