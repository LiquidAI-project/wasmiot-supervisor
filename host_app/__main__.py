"""Main entry point for the supervisor."""

import os
from .utils.configuration import INSTANCE_PATH

# Set wasmiot-orchestrator logging endpoint to send logs to the orchestrator. ex-http://172.21.0.3:3000/device/logs
os.environ.setdefault("WASMIOT_LOGGING_ENDPOINT", "")


if __name__ == "__main__":
    print("Starting program")

    import dotenv
    dotenv.load_dotenv()

    # Have to setup environment variables before importing flask app
    os.environ.setdefault("WASMIOT_SUPERVISOR_NAME", "host_app")
    os.environ.setdefault("WASMIOT_SUPERVISOR_PORT", "5000")
    os.environ.setdefault("SUPERVISOR_NAME", os.environ.get("WASMIOT_SUPERVISOR_NAME"))
    os.environ.setdefault("SUPERVISOR_PORT", os.environ.get("WASMIOT_SUPERVISOR_PORT"))

    # support three variables for setting up name and port
    os.environ.setdefault("FLASK_APP", os.environ.get("SUPERVISOR_NAME"))
    os.environ.setdefault("FLASK_PORT", os.environ.get("SUPERVISOR_PORT"))
    os.environ.setdefault("FLASK_ENV", "development")
    os.environ.setdefault("FLASK_DEBUG", "1")

    from host_app.flask_app import app as flask_app

    # Set wasmiot-orchestrator logging endpoint to send logs to the orchestrator. ex-http://172.21.0.3:3000/device/logs
    if orchestrator_url := os.environ.get("WASMIOT_ORCHESTRATOR_URL"):
        os.environ.setdefault("WASMIOT_LOGGING_ENDPOINT", f"{orchestrator_url}/device/logs")

    debug = bool(os.environ.get("FLASK_DEBUG"))


    app = flask_app.create_app(instance_path=INSTANCE_PATH)
    port_number = int(os.environ.get("FLASK_PORT"))

    app.run(debug=debug, host="0.0.0.0", port=port_number, use_reloader=False)
