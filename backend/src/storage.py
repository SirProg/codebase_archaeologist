"""Subida a S3, URL prefirmada y cache diaria de expedientes."""

import logging
import os

import boto3
from botocore.exceptions import ClientError

log = logging.getLogger(__name__)

BUCKET = os.environ.get("BUCKET_NAME", "")
EXPIRACION = int(os.environ.get("URL_EXPIRACION_SEGUNDOS", "604800"))  # 7 días

_s3 = None


def _cliente():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3")
    return _s3


def existe(key: str) -> bool:
    """¿Ya excavamos este repo hoy? Ahorra tokens y hace la demo instantánea."""
    if not BUCKET:
        return False
    try:
        _cliente().head_object(Bucket=BUCKET, Key=key)
        return True
    except ClientError:
        return False


def subir(key: str, contenido: str, content_type: str = "text/html; charset=utf-8") -> None:
    # Sin ContentType el navegador descarga el archivo en vez de renderizarlo.
    _cliente().put_object(
        Bucket=BUCKET,
        Key=key,
        Body=contenido.encode("utf-8"),
        ContentType=content_type,
    )


def leer(key: str) -> str:
    obj = _cliente().get_object(Bucket=BUCKET, Key=key)
    return obj["Body"].read().decode("utf-8")


def url_prefirmada(key: str) -> str:
    return _cliente().generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": key},
        ExpiresIn=EXPIRACION,
    )
