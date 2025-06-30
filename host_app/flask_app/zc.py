"""
Zeroconf registration for supervisor
"""

import logging
import os
import socket
import threading
import time
from typing import Callable
from flask import Flask
import requests
from zeroconf import EventLoopBlocked, NonUniqueNameException, ServiceInfo, Zeroconf

from host_app.flask_app.app import get_listening_address


class CustomFormatter(logging.Formatter):
    """Formatter for the log output from Zeroconf module."""
    def format(self, record):
        fmt = "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter(fmt, datefmt)
        return formatter.format(record)


# some add-hoc code to set up logging that uses stdout and does not produce context warnings
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
if os.environ.get("FLASK_DEBUG") != "1":
    handler.setLevel(logging.INFO)
    logger.setLevel(logging.INFO)
else:
    handler.setLevel(logging.DEBUG)
    logger.setLevel(logging.DEBUG)
handler.setFormatter(CustomFormatter())
logger.addHandler(handler)

# Url path to register service to orchestrator
URL_BASE_PATH = "/file/device/discovery/register"


def wait_to_be_ready(app: Flask, callback: Callable, args=()):
    """
    Wait until the app is ready to serve requests
    """
    def _callback(app: Flask, callback: Callable):
        app.logger.info("Waiting for app to be ready to call callback %r", callback.__name__)
        while True:
            try:
                # This is a hack to wait for the app to be ready. It's not
                # perfect, but it's the best we can do with Flask.

                # Wait for socket to be open
                with socket.create_connection(get_listening_address(app), timeout=1):
                    app.logger.debug("App is ready, calling callback %r", callback.__name__)
                    break

            except ConnectionRefusedError as exc:
                app.logger.debug("Waiting for app to be ready: %s", exc)
                time.sleep(1)
            except Exception as exc:  # pylint: disable=broad-except
                app.logger.error("Error while waiting for app to be ready: %s", exc, exc_info=True)
                break

        return callback(*args)

    threading.Thread(target=_callback, args=(app, callback)).start()


def register_services_to_orchestrator(service_info: ServiceInfo, orchestrator_url):
    """
    Register services from zeroconf to orchestrator
    """

    data={
        "name": service_info.get_name(),
        "type": service_info.type,
        "port": service_info.port,
        "properties": service_info.decoded_properties,
        "addresses": service_info.parsed_addresses(),
        "host": service_info.server
    }

    try:
        res = requests.post(orchestrator_url, json=data, timeout=10)
        if not res.ok:
            logger.error("Failed to register service to orchestrator: %r", res.text, extra={"response": res})
            return False
    except requests.RequestException as exc:
        logger.error("Network error while registering service to orchestrator: %r", exc, exc_info=True)
        return False
    finally:
        logger.debug("Service registered to orchestrator: %r", data)
    return True


class WebthingZeroconf:
    """
    Flask extension for registering a webthing with zeroconf
    """

    app: Flask
    zeroconf: Zeroconf
    service_info: ServiceInfo

    def __init__(self, app: Flask):
        """
        Register flask extension for zeroconf.
        """
        self.app = app
        self.zeroconf = Zeroconf()
        app.extensions['zc'] = self

        # How long to wait (in seconds) before renewing the registration
        # if no health checks have been done by the orchestrator (default: 15 minutes)
        self.register_renewal_time: float = float(app.config.get("REGISTER_RENEWAL_TIME", 900))
        self.last_register_time: float = time.time()

        server_name = app.config['SERVER_NAME'] or socket.gethostname()
        host, port = get_listening_address(app)

        properties={
            'path': '/',
            'tls': 1 if app.config.get("PREFERRED_URL_SCHEME") == "https" else 0,
            'address': socket.inet_ntoa(socket.inet_aton(host)),
        }

        self.service_info = ServiceInfo(
            type_='_webthing._tcp.local.',
            name=f"{app.name}._webthing._tcp.local.",
            addresses=[socket.inet_aton(host)],
            port=port,
            properties=properties,
            server=f"{server_name}.local.",
        )

        wait_to_be_ready(app, self.register)
        self.start_timeout_monitor()

    def report_health_check(self):
        """
        Resets the last register time to the current time.
        This method should be called when there has been a health check,
        and thus it can be assumed that the registration has been successful.
        """
        self.last_register_time = time.time()

    def register(self):
        """
        Broadcast the service to the network

        Starts the zeroconf service and if :prop:`Flask.config.ORCHESTRATOR_URL` is set,
        registers the service to the orchestrator.
        """
        logger.debug("Starting zeroconf service broadcast for %r", self.service_info.name)
        try:
            self.zeroconf.register_service(self.service_info)
        except (NonUniqueNameException, EventLoopBlocked) as error:
            logger.error("Failed to register service to zeroconf: %r", error, exc_info=True)

        # Register service to orchestrator if ORCHESTRATOR_URL is set
        if orchestrator_url := self.app.config.get("ORCHESTRATOR_URL"):
            orchestrator_url += URL_BASE_PATH
            register_services_to_orchestrator(self.service_info, orchestrator_url)
        else:
            logger.debug("ORCHESTRATOR_URL is not set, skipping manual registration")

        self.last_register_time = time.time()

    def teardown_zeroconf(self):
        """
        Stop advertising mdns services and tear down zeroconf.
        """
        try:
            self.zeroconf.unregister_service(self.service_info)
        except TimeoutError:
            logger.debug("Timeout while unregistering mdns services", exc_info=True)

        self.zeroconf.close()

    def start_timeout_monitor(self):
        """
        Start a background thread to monitor the health check timeout.
        """
        threading.Thread(target=self._monitor_timeout, daemon=True).start()

    def _monitor_timeout(self):
        """
        Monitor the health check timeout and restarts the mDNS service if needed.
        """
        while True:
            time_since_last_health_check = time.time() - self.last_register_time

            if time_since_last_health_check > self.register_renewal_time:
                logger.info("Health check timeout exceeded, re-registering service")

                self.teardown_zeroconf()
                time.sleep(5)  # Wait a bit before restarting

                self.zeroconf = Zeroconf()
                self.app.extensions['zc'] = self
                self.register()

            time.sleep(10)  # Check every 10 seconds

    def __del__(self):
        self.teardown_zeroconf()
