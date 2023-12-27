import logging
import os
from typing import Literal, Optional

import pandas as pd
from google.auth import credentials
from google.cloud import bigquery, bigquery_storage
from google.oauth2 import service_account

from config.constants import GOOGLE_CREDENTIALS, PROJECT_ID, SCOPES


def get_google_credentials() -> credentials.Credentials:
    """Returns Google Service account credentials."""
    google_credentials_path = os.environ[GOOGLE_CREDENTIALS]
    credentials = service_account.Credentials.from_service_account_file(
        google_credentials_path,
        scopes=SCOPES,
    )
    return credentials


def query_data_from_bq(query: str) -> pd.DataFrame:
    """Queries data from BigQuery and returns a pandas DataFrame.

    Args:
        query (str): The SQL query string to execute.

    Returns:
        pd.DataFrame: The queried data as a pandas DataFrame.
    """
    with bigquery.Client(
        credentials=get_google_credentials(),
        project=PROJECT_ID,
    ) as bq_client, bigquery_storage.BigQueryReadClient(
        credentials=get_google_credentials(),
    ) as bqstorage_client:
        query_output_df = (
            bq_client.query(query)
            .to_arrow(bqstorage_client=bqstorage_client, progress_bar_type='tqdm')
            .to_pandas()
        )
    return query_output_df


def fetch_and_cache_data_from_bq(
    query: str,
    file_path: Optional[str] = None,
    file_type: str = 'feather',
    read_file: bool = True,
) -> pd.DataFrame:
    """Tries to load data from a file.

    If the file doesn't exist, queries data from BigQuery and saves it to a file.

    Args:
        query (str): The SQL query string to execute.
        file_path (Optional[str]): The file path to read from or write to.
        file_type (Optional[str]): The file type, either 'feather' or 'csv'.
        read_file (Optional[bool]): Whether to read the file if it exists.

    Returns:
        pd.DataFrame: The queried or loaded data as a pandas DataFrame.
    """
    if file_type not in ['feather', 'csv']:
        raise ValueError(f'Filetype {file_type} not supported. Use feather or csv.')

    if file_path and read_file:
        try:
            logging.info(f'Loading data from {file_path}')
            if file_type == 'feather':
                data = pd.read_feather(file_path)
            elif file_type == 'csv':
                data = pd.read_csv(file_path)
        except FileNotFoundError:
            logging.info(f'File {file_path} not found. Fetching data from BigQuery.')
            data = query_data_from_bq(query)
            if file_type == 'feather':
                data.to_feather(file_path)
            elif file_type == 'csv':
                data.to_csv(file_path, index=False)
    else:
        logging.info('Fetching data from BigQuery.')
        data = query_data_from_bq(query)
    return data


def write_to_bq(
    dataframe: pd.DataFrame,
    table_name: str,
    write_disposition: Literal[
        'WRITE_TRUNCATE',
        'WRITE_APPEND',
        'WRITE_EMPTY',
    ] = 'WRITE_TRUNCATE',
) -> None:
    """Writes a pandas DataFrame to a BigQuery table.

    write_disposition options:
    - WRITE_TRUNCATE: If the table already exists, BigQuery overwrites the table data.
    - WRITE_APPEND: If the table already exists, BigQuery appends the data to the table.
    - WRITE_EMPTY: If the table already exists and contains data, a 'duplicate' error
        is returned in the job result.

    Args:
        dataframe (pd.DataFrame): The pandas DataFrame to write to BigQuery.
        table_name (str): The name of the table to write to.
        write_disposition (Literal['WRITE_TRUNCATE', 'WRITE_APPEND', 'WRITE_EMPTY']):
            The write disposition mode. Defaults to 'WRITE_TRUNCATE'.
    """
    with bigquery.Client(
        credentials=get_google_credentials(),
        project=PROJECT_ID,
    ) as bq_client:
        bq_client.load_table_from_dataframe(
            dataframe,
            table_name,
            job_config=bigquery.LoadJobConfig(
                write_disposition=write_disposition,
            ),
        )
    logging.info(f'Data written to {table_name} in BigQuery.')
