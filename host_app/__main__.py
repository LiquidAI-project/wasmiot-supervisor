#from .app import create_app, teardown_zeroconf
import os

from .utils.configuration import INSTANCE_PATH

from host_app.flask_app import app as flask_app

if __name__ == "__main__":
    print("Starting program")

    import dotenv
    dotenv.load_dotenv()

    # Have to setup environment variables before importing flask app
    os.environ.setdefault("FLASK_APP", "host_app")
    os.environ.setdefault("FLASK_ENV", "development")
    os.environ.setdefault("FLASK_DEBUG", "1")
    # Set wasmiot-orchestrator logging endpoint to send logs to the orchestrator. ex-http://172.21.0.3:3000/device/logs

    if orchestrator_url := os.environ.get("WASMIOT_ORCHESTRATOR_URL"):
        os.environ.setdefault("WASMIOT_LOGGING_ENDPOINT", f"{orchestrator_url}/device/logs")

    #print('starting modules')
    #wasm_daemon = threading.Thread(name='wasm_daemon',
    #                               daemon=True,
    #                               target=wa.start_modules,
    #                                 )
    #wasm_daemon.start()

    debug = bool(os.environ.get("FLASK_DEBUG", 0))


    app = flask_app.create_app(instance_path=INSTANCE_PATH)

    app.run(debug=debug, host="0.0.0.0", use_reloader=False)

