import io
import logging
from contextlib import contextmanager
from typing import Dict, List, Optional

import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from utils.bq_utils import get_google_credentials


@contextmanager
def drive_service_context():
    """A context manager for the Google Drive service."""
    drive_service = None
    try:
        creds = get_google_credentials()
        drive_service = build(
            'drive',
            'v3',
            credentials=creds,
            cache_discovery=False,
        )
        yield drive_service
    except Exception as exception:
        raise RuntimeError(
            f'Error authorizing Google Drive API: {exception}',
        ) from exception
    finally:
        if drive_service:
            drive_service.close()


def list_files_in_folder(folder_id: str) -> List[Dict[str, str]]:
    """List all files in a specific Google Drive folder.

    Do not forget to share folder access with your service account:
    name-surname@surfshark-analytics.iam.gserviceaccount.com.

    Args:
        folder_id (str): The ID of the Google Drive folder.

    Returns:
        List[Dict[str, str]]: A list of dictionaries containing file IDs and names.
    """
    with drive_service_context() as service:
        try:
            query = (
                f"'{folder_id}' in parents and trashed = false and "
                f"mimeType!='application/vnd.google-apps.folder'"
            )
            results = (
                service.files()
                .list(
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    q=query,
                    fields='nextPageToken, files(id, name)',
                )
                .execute()
            )
            items = results.get('files', [])
            if not items:
                logging.info('No files found.')
                return []
            else:
                return items
        except HttpError as error:
            logging.info(f'An error occurred: {error}')
            return []


def read_file_from_drive(
    file_id: str,
    **kwargs,
) -> Optional[pd.DataFrame]:
    """Reads a file (CSV, Excel, txt) from Google Drive and returns it as a DataFrame.

    Args:
        file_id (str): The ID of the file to read from Google Drive.
        **kwargs: Additional keyword arguments to pass to the Pandas reading function.

    Returns:
        Optional[pd.DataFrame]: The content of the file as a pandas DataFrame, or None.
    """
    with drive_service_context() as service:
        try:
            file_metadata = service.files().get(fileId=file_id, fields='name').execute()
            file_name = file_metadata.get('name', '')
            file_extension = file_name.split('.')[-1] if '.' in file_name else ''

            if file_extension in ['csv', 'txt', 'xlsx']:
                request = service.files().get_media(fileId=file_id)
            else:
                raise ValueError('Unsupported file type: ' + file_extension)

            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            fh.seek(0)

            if file_extension in ['csv', 'txt']:
                return pd.read_csv(fh, **kwargs)
            elif file_extension == 'xlsx':
                return pd.read_excel(fh, **kwargs)
            else:
                raise ValueError('Unsupported file type: ' + file_extension)

        except HttpError as error:
            raise HttpError(f'An error occurred: {error}') from error
