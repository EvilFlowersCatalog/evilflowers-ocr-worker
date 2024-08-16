import os
import ocrmypdf
from celery import Celery

# Initialize Celery app with broker and include new settings
app = Celery("evilflowers_ocr_worker", broker=os.getenv("BROKER", "redis://localhost:6379/0"))

# Set broker_connection_retry_on_startup to True to avoid the warning
app.conf.update(
    broker_connection_retry_on_startup=True,
)


@app.task(bind=True)
def ocr(self, source: str, destination: str, language: str):
    try:
        ocrmypdf.ocr(source, destination, deskew=True, rotate_pages=True, language=[language])
    except Exception as exc:
        # Optional: Log the exception or perform other error handling here
        self.retry(exc=exc, countdown=60, max_retries=3)
