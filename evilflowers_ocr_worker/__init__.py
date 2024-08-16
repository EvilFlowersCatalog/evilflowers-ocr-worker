import os
import ocrmypdf
import logging
from celery import Celery

# Initialize logger
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Initialize Celery app with broker and include new settings
app = Celery("evilflowers_ocr_worker", broker=os.getenv("BROKER", "redis://localhost:6379/0"))

# Set broker_connection_retry_on_startup to True to avoid the warning
app.conf.update(
    broker_connection_retry_on_startup=True,
)

# Optional: Set up OpenTelemetry tracing if available
try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.instrumentation.celery import CeleryInstrumentor

    # Set up OpenTelemetry tracing
    service_name = os.getenv("OTEL_SERVICE_NAME", "evilflowers-ocr-worker")
    resource = Resource(attributes={"service.name": service_name})
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # Instrument Celery with OpenTelemetry
    CeleryInstrumentor().instrument()

    logger.info("OpenTelemetry tracing initialized.")

except ImportError:
    logger.warning("OpenTelemetry not installed. Tracing disabled.")


@app.task(bind=True)
def ocr(self, source: str, destination: str, language: str):
    logger.info(f"OCR task started: {source} -> {destination}")
    try:
        ocrmypdf.ocr(source, destination, deskew=True, rotate_pages=True, language=[language])
    except Exception as exc:
        logger.error(f"OCR task failed: {exc}")
        self.retry(exc=exc, countdown=60, max_retries=3)
