"""
1 - Module responsible for reading and cleaning the input file.
2 - Finds .xlsx files in PATH_IN and returns a clean DataFrame.
3 - Centralises the reading fixes so the execution modules do not repeat them.

Reading (which depends on the disk) stays in the class; cleaning is the pure
function clean_dataframe, isolated so it can be tested and reused with no I/O.
"""

from pathlib import Path

import pandas as pd

from resources.settings import get_settings
from resources.Tools.logs import Logs


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a cleaned version of the DataFrame, leaving the original untouched.

    Fixes applied:
        - Strip the column names (avoids KeyError from a hidden space)
        - Drop entirely empty columns
        - Drop entirely empty rows

    It uses set_axis instead of assigning to df.columns: the assignment would
    mutate the DataFrame it received, which would stop the function being pure.

    Args:
        df: DataFrame exactly as it came from the file, uncleaned.

    Returns:
        The cleaned DataFrame. The original stays intact.
    """
    return (
        df
        .set_axis(df.columns.str.strip(), axis=1)
        .dropna(axis=1, how='all')
        .dropna(axis=0, how='all')
    )


class FileReader:
    """Reads and cleans the .xlsx files found in PATH_IN."""

    def __init__(self, logs: Logs, path_in: str | Path | None = None):
        """
        Initialises with the input folder.

        Args:
            logs: Logs instance used to record the operations.
            path_in: Folder to look for the .xlsx files in. Omitted, it falls
                back to get_settings().PATH_IN — and only in that case is
                config.json read, which is what allows testing against a
                temporary folder.
        """
        self.logs = logs
        self.path_in = Path(path_in or get_settings().PATH_IN)

    def get_xlsx_files(self) -> list[Path]:
        """
        Returns the .xlsx files in PATH_IN, from the oldest to the newest.

        Returns:
            List of Paths for the .xlsx files found.

        Raises:
            FileNotFoundError: If the PATH_IN folder does not exist, or holds
                no .xlsx files.
        """
        if not self.path_in.exists():
            raise FileNotFoundError(f'PATH_IN folder not found: {self.path_in}')

        files = sorted(
            [
                file
                for file in self.path_in.iterdir()
                if file.is_file() and file.suffix.lower() == '.xlsx'
            ],
            key=lambda file: file.stat().st_mtime,
        )

        if not files:
            raise FileNotFoundError(f'No .xlsx file found in PATH_IN: {self.path_in}')

        self.logs.info(f'{len(files)} .xlsx file(s) found in PATH_IN.')
        return files

    def read_file(self) -> pd.DataFrame:
        """
        Reads the .xlsx files in PATH_IN, cleans them and returns one merged
        DataFrame.

        The cleaning lives in clean_dataframe.

        Returns:
            A pandas DataFrame with the cleaned data, ready to use.
        """
        dataframes = []
        for file in self.get_xlsx_files():
            self.logs.info(f'Reading file: {file.name}.')
            dataframes.append(clean_dataframe(pd.read_excel(file)))

        return pd.concat(dataframes, ignore_index=True)
