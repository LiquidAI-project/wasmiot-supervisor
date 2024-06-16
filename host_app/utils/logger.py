# utils/logger.py
import logging
from logging.handlers import HTTPHandler, QueueHandler, QueueListener
import os
import requests
import json
import queue
import socket
from flask import current_app


class JsonFormatter(logging.Formatter):
    """
    Formats the log messages as JSON strings.
    """
    def format(self, record):
        """
        Format the specified record as json string.
        """
        from host_app.flask_app.app import get_listening_address  # pylint: disable=import-outside-toplevel

        # When using get_listening_address I get an error about the app context not being available.
        # Tried fixing by adding "with current_app.app_context():" but it didn't work.
        #ip, _ = get_listening_address(current_app)
        ip = os.environ.get('WASMIOT_SUPERVISOR_IP')
        if not ip:
            ip = socket.gethostbyname(socket.gethostname())
        
        record.asctime = self.formatTime(record, self.datefmt)
        json_message = {
            "timestamp": record.asctime,
            "loglevel": record.levelname,
            "message": record.getMessage(),
            "funcName": record.funcName,
            "deviceName": record.name,
            "deviceIP": ip,
        }

        # Add the extra information to the JSON message
        if hasattr(record, 'request'):
            json_message['request_id'] = record.request.request_id
            json_message['deployment_id'] = record.request.deployment_id
            json_message['module_name'] = record.request.module_name

        return json.dumps(json_message)

class RequestsHandler(HTTPHandler):
    """
    Sends the log messages to a specified URL.
    """
    def __init__(self, request):
        """
        Initialize the handler with a request object.
        """
        self.request = request
        self.logging_endpoint = os.getenv('WASMIOT_LOGGING_ENDPOINT', None)
        self.queue = queue.Queue(-1)
        self.queue_handler = QueueHandler(self.queue)

        try:
            """
            If the request has a remote address, use it as the host for the HTTPHandler
            Otherwise, use 'localhost' as the host
            """
            if self.logging_endpoint:
                super().__init__(self.logging_endpoint, '/device/logs', method='POST')
            elif hasattr(self.request, 'remote_addr'):
                super().__init__(self.request.remote_addr, '/device/logs', method='POST')
            else:
                super().__init__('localhost', '/device/logs', method='POST')
        except Exception as e:
            print(f"Error initializing RequestsHandler: {e}")

        self.queue_listener = QueueListener(self.queue, self)

    def emit(self, record):
        self.queue_handler.emit(record)

    def start(self):
        self.queue_listener.start()

    def stop(self):
        self.queue_listener.stop()

    def handle(self, record):
        """
        Conditionally emit the specified logging record.
        """
        log_entry = self.format(record)
        try:
            """
            If the request has a remote address, send the log to that address
            Otherwise, print an error message
            """
            if self.logging_endpoint:
                url = f"{self.logging_endpoint}"
                response = requests.post(url, data={'logData': log_entry})
                # print(f"Response: {response.status_code}, {response.text}")
            elif hasattr(self.request, 'remote_addr'):
                url = f"http://{self.request.remote_addr}:3000/device/logs"
                response = requests.post(url, data={'logData': log_entry})
                print(f"Sent log: {log_entry}")
                # print(f"Response: {response.status_code}, {response.text}")
            else:
                print("No remote address available for logging.")
        except Exception as e:
            print(f"Error sending log: {e}")

def setup_logger(request):
    """
    Set up a logger with a RequestsHandler.
    """
    # Create a logger with the name from the "FLASK_APP" environment variable
    logger = logging.getLogger(os.environ["FLASK_APP"])

    # Set the logging level to DEBUG
    logger.setLevel(logging.DEBUG)

    # Create a RequestsHandler with the given request and set its formatter
    handler = RequestsHandler(request)
    formatter = JsonFormatter()
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger

def get_logger(request):
    """
    Get a logger, setting it up if necessary.
    """
    logger_name = os.environ["FLASK_APP"]

    # Get the logger with the given name
    logger = logging.getLogger(logger_name)

    # Check if the logger has any handlers of type RequestsHandler
    # If it doesn't, it means the logger hasn't been set up yet
    if not any(isinstance(handler, RequestsHandler) for handler in logger.handlers):
        logger = setup_logger(request)

    return logger