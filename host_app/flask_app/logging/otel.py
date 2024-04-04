"""
OpenTelemetry integration for Flask application.
"""

from logging import getLogger
from opentelemetry import trace
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource

from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.jinja2 import Jinja2Instrumentor
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor

from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from host_app.flask_app.app import FlaskApp


logger = getLogger(__name__)

EXT_NAME = 'otel_tracer'

def init_app(app: FlaskApp):
    """
    Integrate opentelemetry into application.
    
    ..todo::
        - Add support for metrics.
    """
    
    logger.debug("Initializing opentelemetry.")

    # This flag is set by FlaskInstrumentor.instrument_app() to avoid double instrumentation
    if hasattr(app, '_is_instrumented_by_opentelemetry'):
        logger.warning("OpenTelemetry already initialized.")
        return

    from host_app import __version__  # pylint: disable=import-outside-toplevel

    resource = Resource(attributes={
        SERVICE_NAME: app.import_name,
        SERVICE_VERSION: __version__,
    })

    # Detect if running in a container and add the appropriate attributes
    # TODO: depends on opentelemetry-resource-detector-container package, which is not yet available
    #from opentelemetry.resource.detector.container import ContainerResourceDetector
    #if container_resource := ContainerResourceDetector().detect():
    #    resource = resource.merge(container_resource)

    app.extensions[EXT_NAME] = TracerProvider(resource=resource)

    span_processor = BatchSpanProcessor(OTLPSpanExporter())
    trace.set_tracer_provider(app.extensions[EXT_NAME])
    app.extensions[EXT_NAME].add_span_processor(span_processor)


    FlaskInstrumentor().instrument_app(app, tracer_provider=app.extensions[EXT_NAME])
    RequestsInstrumentor().instrument(tracer_provider=app.extensions[EXT_NAME])
    LoggingInstrumentor().instrument(tracer_provider=app.extensions[EXT_NAME])
    Jinja2Instrumentor().instrument(tracer_provider=app.extensions[EXT_NAME])

    # TODO: requires support for metrics
    SystemMetricsInstrumentor().instrument(tracer_provider=app.extensions[EXT_NAME])

    setattr(app, 'tracer', app.extensions[EXT_NAME])
