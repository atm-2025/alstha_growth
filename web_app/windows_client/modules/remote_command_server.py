import threading
import logging
from flask import Flask, request, jsonify

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_command_server(command_callback, port=5005):
    try:
        logger.info(f"Starting command server on port {port}")
        
        app = Flask(__name__)

        @app.route('/', methods=['GET'])
        def test_endpoint():
            logger.info("Test endpoint accessed")
            return jsonify({"status": "ok", "message": "Command server is running", "port": port})

        @app.route('/command', methods=['POST'])
        def handle_command():
            try:
                data = request.get_json()
                action = data.get('action')
                logger.info(f"Received command: {action}")
                result = command_callback(action)
                logger.info(f"Command result: {result}")
                return jsonify({"status": "ok", "result": result})
            except Exception as e:
                logger.error(f"Error handling command: {e}")
                return jsonify({"status": "error", "result": str(e)}), 500

        def run_server():
            try:
                logger.info(f"Command server thread starting on port {port}")
                app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
            except Exception as e:
                logger.error(f"Failed to start command server: {e}")
                raise

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        
        logger.info("Command server startup initiated successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error in start_command_server: {e}")
        return False 