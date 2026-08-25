"""
Reads the .xlsx files in PATH_IN and returns one clean DataFrame.

Reading touches the disk and stays in the class; cleaning is the pure function
clean_dataframe, isolated so it can be tested with no I/O at all.
"""

from pathlib import Path

import pandas as pd

from resources.settings import get_settings
from resources.Tools.logs import Logs


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    A cleaned copy: column names stripped (a hidden space becomes a KeyError
    three layers down), fully empty rows and columns dropped.

    set_axis rather than assigning to df.columns, because the assignment would
    mutate the caller's DataFrame and this function would stop being pure.
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
        path_in omitted falls back to get_settings().PATH_IN — and *only* in
        that case is config.json read, which is what lets the tests point this
        at a temporary folder with no configuration on the machine.
        """
        self.logs = logs
        self.path_in = Path(path_in or get_settings().PATH_IN)

    def get_xlsx_files(self) -> list[Path]:
        """
        The .xlsx files in PATH_IN, oldest first. Raises FileNotFoundError when
        the folder is missing or holds none — both are setup mistakes.
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
        Every .xlsx in PATH_IN, cleaned and concatenated into one DataFrame.
        """
        dataframes = []
        for file in self.get_xlsx_files():
            self.logs.info(f'Reading file: {file.name}.')
            dataframes.append(clean_dataframe(pd.read_excel(file)))

        return pd.concat(dataframes, ignore_index=True)
