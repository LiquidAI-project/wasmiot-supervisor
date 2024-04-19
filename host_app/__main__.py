#from .app import create_app, teardown_zeroconf
import os

# Have to setup environment variables before importing flask app
os.environ.setdefault("FLASK_APP", "host_app")
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("FLASK_DEBUG", "1")

# Set wasmiot-orchestrator logging endpoint to send logs to the orchestrator. ex-http://172.21.0.3:3000/device/logs
os.environ.setdefault("WASMIOT_LOGGING_ENDPOINT", "")

from .utils.configuration import INSTANCE_PATH

from host_app.flask_app import app as flask_app

if __name__ == "__main__":
    print("Starting program")


    #print('starting modules')
    #wasm_daemon = threading.Thread(name='wasm_daemon',
    #                               daemon=True,
    #                               target=wa.start_modules,
    #                                 )
    #wasm_daemon.start()

    app = flask_app.create_app(instance_path=INSTANCE_PATH)

    app.run(debug=True, host="0.0.0.0")

