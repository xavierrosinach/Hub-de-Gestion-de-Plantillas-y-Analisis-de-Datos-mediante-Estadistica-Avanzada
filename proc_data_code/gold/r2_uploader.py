import os
import mimetypes

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from dotenv import load_dotenv


# Sube los datos a un bucket de Cloudflare R2
class R2Uploader:

    FOLDERS = ["images/manager", "images/team", "images/player", "entities/manager", "entities/player", "entities/team", "info"]

    # Inicializa el cliente de R2 y crea las carpetas
    def __init__(self):

        load_dotenv()

        self.bucket_name = os.environ["R2_BUCKET_NAME"]
        public_base_url = os.environ.get("R2_PUBLIC_URL")
        self.public_base_url = public_base_url.rstrip("/") if public_base_url else None

        self.client = boto3.client("s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com", aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"], aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], config=Config(signature_version="s3v4"), region_name="auto")
        self._ensure_folders()

    # API de subida de un path a una carpeta (mismo nombre que el archivo en local)
    def upload(self, path: str, folder: str) -> str | None:

        if not os.path.isfile(path):
            raise FileNotFoundError(f"No existe el archivo: {path}")

        filename = os.path.basename(path)
        key = f"{folder.strip('/')}/{filename}"

        # Detectar el tipo MIME para que el navegador lo sirva correctamente
        content_type, _ = mimetypes.guess_type(path)
        extra_args = {"ContentType": content_type} if content_type else {}

        self.client.upload_file(path, self.bucket_name, key, ExtraArgs=extra_args)
        return self.public_url(key)

    # Sube datos en memoria
    def upload_bytes(self, data: bytes, folder: str, filename: str, content_type: str | None = None) -> str | None:
        key = f"{folder.strip('/')}/{filename}"
        kwargs = {"Bucket": self.bucket_name, "Key": key, "Body": data}
        if content_type:
            kwargs["ContentType"] = content_type
        self.client.put_object(**kwargs)
        return self.public_url(key)

    # Construye el enlace público
    def public_url(self, key: str) -> str | None:
        if self.public_base_url:
            return f"{self.public_base_url}/{key}"
        return None

    # Crea un objeto para carpetas que noexisten
    def _ensure_folders(self) -> None:
        for folder in self.FOLDERS:
            key = folder.rstrip("/") + "/"
            if not self._object_exists(key):
                self.client.put_object(Bucket=self.bucket_name, Key=key, Body=b"")

    def _object_exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
                return False
            raise