# utils/logger.py
import logging
from logging.handlers import HTTPHandler
import os
import requests

# Define a custom handler for HTTP logs
class RequestsHandler(HTTPHandler):
    # Initialize the handler with a request object
    def __init__(self, request):
        # Store the request object for later use
        self.request = request
        try:
            # If the request has a remote address, use it as the host for the HTTPHandler
            if hasattr(self.request, 'remote_addr'):
                super().__init__(self.request.remote_addr, '/device/logs', method='POST')
            else:
                # If the request doesn't have a remote address, use 'localhost' as the host
                super().__init__('localhost', '/device/logs', method='POST')
        except Exception as e:
            print(f"Error initializing RequestsHandler: {e}")

    # Emit a log record
    def emit(self, record):
        log_entry = self.format(record)
        try:
            # If the request has a remote address, send the log to that address
            if hasattr(self.request, 'remote_addr'):
                url = f"http://{self.request.remote_addr}:3000/device/logs"
                response = requests.post(url, data={'logData': log_entry})
                print(f"Sent log: {log_entry}")
                # print(f"Response: {response.status_code}, {response.text}")
            else:
                print("No remote address available for logging.")
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to the URL: {e}")

# Set up a logger with a RequestsHandler
def setup_logger(request):
    # Create a logger with the name from the "FLASK_APP" environment variable
    logger = logging.getLogger(os.environ["FLASK_APP"])

    # Set the logging level to DEBUG
    logger.setLevel(logging.DEBUG)

    # Create a RequestsHandler with the given request and set its formatter
    handler = RequestsHandler(request)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger

# Get a logger, setting it up if necessary
def get_logger(request):
    logger_name = os.environ["FLASK_APP"]

    # Get the logger with the given name
    logger = logging.getLogger(logger_name)

    # Check if the logger has any handlers
    # If it doesn't, it means the logger hasn't been set up yet
    if not logger.hasHandlers():
        logger = setup_logger(request)

    return logger