"""
OpenTelemetry integration for Flask application.
"""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource

from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from flask import Flask

from logging import getLogger

logger = getLogger(__name__)

def init_app(app):
    """
    Integrate opentelemetry into application.
    """
    logger.debug("Initializing opentelemetry.")

    from host_app import __version__  # pylint: disable=import-outside-toplevel

    resource = Resource(attributes={
        SERVICE_NAME: app.import_name,
        SERVICE_VERSION: __version__,
    })

    app.tracer = TracerProvider(resource=resource)

    span_processor = BatchSpanProcessor(OTLPSpanExporter())
    app.tracer.add_span_processor(span_processor)
    
    trace.set_tracer_provider(app.tracer)

    FlaskInstrumentor().instrument_app(app)
    RequestsInstrumentor().instrument()
    LoggingInstrumentor().instrument()
