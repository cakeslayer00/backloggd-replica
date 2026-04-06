import io
import os
import tempfile
from PIL import Image
from minio import Minio
from app.core.celery_app import celery_app
from app.core.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


engine = create_engine(
    f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)
SessionLocal = sessionmaker(bind=engine)


def get_minio_client():
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def ensure_bucket_exists():
    client = get_minio_client()
    if not client.bucket_exists(settings.MINIO_BUCKET):
        client.make_bucket(settings.MINIO_BUCKET)
        print(f"[MINIO] Created bucket: {settings.MINIO_BUCKET}")


@celery_app.task(bind=True, max_retries=3)
def compress_and_upload_image(self, screenshot_id: int, temp_path: str):
    print(f"[IMAGE] Processing screenshot {screenshot_id}")
    print(f"[IMAGE] Original file: {temp_path}")
    original_size = os.path.getsize(temp_path)
    print(f"[IMAGE] Original size: {original_size / 1024:.2f} KB")

    try:
        with Image.open(temp_path) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            output = io.BytesIO()
            img.save(output, format="JPEG", quality=85, optimize=True)
            compressed_data = output.getvalue()

        compressed_size = len(compressed_data)
        print(f"[IMAGE] Compressed size: {compressed_size / 1024:.2f} KB")
        print(
            f"[IMAGE] Compression ratio: {(1 - compressed_size / original_size) * 100:.1f}%"
        )

        ensure_bucket_exists()
        client = get_minio_client()

        object_name = f"screenshots/{screenshot_id}_{screenshot_id}.jpg"
        client.put_object(
            settings.MINIO_BUCKET,
            object_name,
            io.BytesIO(compressed_data),
            length=len(compressed_data),
            content_type="image/jpeg",
        )

        file_url = f"{settings.minio_url}/{settings.MINIO_BUCKET}/{object_name}"
        print(f"[IMAGE] Uploaded to: {file_url}")

        session = SessionLocal()
        try:
            from app.models.screenshot import Screenshot

            screenshot = (
                session.query(Screenshot).filter(Screenshot.id == screenshot_id).first()
            )
            if screenshot:
                screenshot.file_url = file_url
                screenshot.file_size_bytes = compressed_size
                session.commit()
                print(f"[IMAGE] Updated database for screenshot {screenshot_id}")
            else:
                print(f"[IMAGE] Screenshot {screenshot_id} not found in database")
        finally:
            session.close()

        if os.path.exists(temp_path):
            os.remove(temp_path)
            print(f"[IMAGE] Cleaned up temp file: {temp_path}")

        return {
            "screenshot_id": screenshot_id,
            "original_size": original_size,
            "compressed_size": compressed_size,
            "file_url": file_url,
        }

    except Exception as e:
        print(f"[IMAGE] Error processing screenshot {screenshot_id}: {e}")
        raise self.retry(exc=e)
