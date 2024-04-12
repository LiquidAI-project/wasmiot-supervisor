"""
Utilities for Flask-endpoint operations etc.
"""

from flask import jsonify
from host_app.utils.logger import get_logger


def endpoint_failed(request, msg="", status_code=500, **additional_fields):
    """
    Helper to construct JSON response for communicating that request to endpoint failed (and log this).

    :request The request that failed
    :msg The message to use in the `status` field of response
    :status_code The status code to use in response
    """
    print(f"{request.method} on '{request.path}': {msg}")
    get_logger(request).error(f"{msg}")

    resp = jsonify({ "status": "error", "result": msg, **additional_fields })
    resp.status_code = status_code
    return resp
