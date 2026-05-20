from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import logging
from dotenv import load_dotenv
import os
app = Flask(__name__)
CORS(app)
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RASA_SERVER_URL = os.environ["RASA_SERVER_URL"]
MIDDLEWARE_HOST = os.environ["MIDDLEWARE_HOST"]
MIDDLEWARE_PORT = int(os.environ["MIDDLEWARE_PORT"])


@app.route('/chat', methods=['POST','GET'])
def chat():
    try:
        data = request.get_json(silent=True)

        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Raw request data: {request.data}")

        if not data:
            logger.warning("No valid JSON data received in request")
            return jsonify({
                "success": False,
                "error": "No valid JSON data provided. Ensure Content-Type is application/json."
            }), 400

        sender = data.get('sender')
        message = data.get('message')

        if not sender or not message:
            logger.warning(f"Missing fields - sender: {sender}, message: {message}")
            return jsonify({
                "success": False,
                "error": "Both 'sender' and 'message' fields are required in the request body."
            }), 400

        logger.info(f"Received message from '{sender}': {message}")

        rasa_payload = {
            "sender": sender,
            "message": message,
            "metadata": data.get("metadata", {})
        }

        rasa_response = requests.post(
            RASA_SERVER_URL,
            json=rasa_payload,
            timeout=100
        )

        if rasa_response.status_code == 200:
            rasa_data = rasa_response.json()
            logger.info(f"Rasa response: {rasa_data}")

            if not rasa_data:
                logger.warning("Rasa returned an empty response")
                return jsonify({
                    "success": True,
                    "responses": [],
                    "warning": "Rasa returned no response. The bot may not have a matching intent."
                }), 200

            return jsonify({
                "success": True,
                "responses": rasa_data
            }), 200

        else:
            logger.error(f"Rasa server error: {rasa_response.status_code} - {rasa_response.text}")
            return jsonify({
                "success": False,
                "error": "Rasa server returned an error.",
                "status_code": rasa_response.status_code,
                "detail": rasa_response.text
            }), 500

    except requests.exceptions.Timeout:
        logger.error("Rasa server timed out")
        return jsonify({
            "success": False,
        }), 504

    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to Rasa server at {RASA_SERVER_URL}")
        return jsonify({
            "success": False,
            "error": f"Cannot connect to Rasa server at {RASA_SERVER_URL}. Please ensure Rasa is running."
        }), 503

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "detail": str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint - checks both middleware and Rasa status"""
    try:
        rasa_health_url = f"http://{MIDDLEWARE_HOST}:5005/"
        rasa_response = requests.get(rasa_health_url, timeout=5)
        rasa_status = "up" if rasa_response.status_code == 200 else "down"
    except Exception as e:
        logger.warning(f"Rasa health check failed: {str(e)}")
        rasa_status = "down"

    return jsonify({
        "middleware": "up",
        "rasa": rasa_status,
        "rasa_url": RASA_SERVER_URL
    }), 200


@app.route('/chat', methods=['OPTIONS'])
def chat_options():
    """Explicitly handle OPTIONS preflight for CORS"""
    return jsonify({"status": "ok"}), 200


if __name__ == '__main__':
    print("=" * 50)
    print("Rasa Middleware Server Starting...")
    print(f"Connecting to Rasa at: {RASA_SERVER_URL}")
    print(f"Middleware will run on: http://{MIDDLEWARE_HOST}:{MIDDLEWARE_PORT}")
    print("=" * 50)

    app.run(host=MIDDLEWARE_HOST, port=MIDDLEWARE_PORT, debug=True)
