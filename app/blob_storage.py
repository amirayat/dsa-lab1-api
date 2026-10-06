"""
app/blob_storage.py
Upload images to Azure Blob Storage.
"""
import os
from typing import Optional

from azure.storage.blob.aio import BlobServiceClient
from azure.core.exceptions import AzureError


async def upload_to_blob(
    blob_name: str,
    data: bytes,
    content_type: str = "image/jpeg",
) -> str:
    """
    Upload bytes to Azure Blob Storage.

    Args:
        blob_name: name of the blob inside the container, e.g. "abc-123.jpg"
        data: raw bytes
        content_type: MIME type (default image/jpeg)

    Returns:
        The full blob URL (https://<account>.blob.core.windows.net/<container>/<blob_name>)

    Raises:
        AzureError if upload fails
    """
    connection_string: Optional[str] = os.environ.get("BLOB_CONNECTION_STRING")
    container: Optional[str] = os.environ.get("BLOB_CONTAINER_NAME")

    if not connection_string:
        raise RuntimeError("BLOB_CONNECTION_STRING is not set")
    if not container:
        raise RuntimeError("BLOB_CONTAINER_NAME is not set")

    blob_service = BlobServiceClient.from_connection_string(connection_string)
    async with blob_service:
        blob_client = blob_service.get_blob_client(container=container, blob=blob_name)

        # overwrite=True is safe because blob_name is a UUID (always unique)
        await blob_client.upload_blob(
            data,
            overwrite=True,
            content_type=content_type,
        )

        return blob_client.url