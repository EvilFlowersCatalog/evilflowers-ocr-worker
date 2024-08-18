import os
import shutil

import ocrmypdf
import logging
from celery import Celery, Task

# Initialize logger
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Initialize Celery app with broker and include new settings
app = Celery("evilflowers_ocr_worker", broker=os.getenv("BROKER", "redis://localhost:6379/0"))

app.conf.event_serializer = "json"
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["application/json"]

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
def ocr(self: Task, source: str, destination: str, language: str):
    logger.info(f"OCR task started: {source} -> {destination}")

    target = f"/tmp/{self.request.id}"
    logger.debug(f"Temporary target: {target}")

    storage_path = os.getenv("STORAGE_PATH", "/mnt/data")
    source = f"{storage_path}/{source}"
    destination = f"{storage_path}/{destination}"

    try:
        ocrmypdf.ocr(source, target, deskew=True, rotate_pages=True, language=[language])
    except Exception as exc:
        logger.error(f"OCR task failed: {exc}")
        return

    shutil.move(target, destination)

    return {"source": source, "target": target, "destination": destination}
