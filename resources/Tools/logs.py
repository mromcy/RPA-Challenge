import logging
import os
import traceback
from datetime import datetime

from botcity.maestro import BotMaestroSDK

from resources.settings import get_settings


class Logs:
    """
    Writes to the console and to a daily file, and forwards errors to Maestro
    when the run has a task_id.

    `_save_log_to_db` is a stub with no effect.
    """

    def __init__(
        self,
        maestro: BotMaestroSDK,
        logger_name: str = 'RPA',
        log_level: int = logging.INFO,
        configure_handler: bool = True,
        logger: logging.Logger | None = None,
    ):
        self.maestro = maestro
        self._local_execution = not maestro.task_id

        self.log_dir = get_settings().PATH_LOGS

        os.makedirs(self.log_dir, exist_ok=True)

        date_str = datetime.now().strftime('%Y-%m-%d')
        log_filename = f'app{date_str}.log'
        log_path = os.path.join(self.log_dir, log_filename)

        if logger:
            self._logger = logger
        else:
            self._logger = logging.getLogger(logger_name)

        if configure_handler:
            if logger is None:
                self._logger.setLevel(log_level)

            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
            )

            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self._logger.addHandler(console_handler)

            file_handler = logging.FileHandler(log_path, encoding='utf-8')
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)

            if logger is None:
                self._logger.propagate = False

    def debug(self, message, *args, **kwargs):
        self._logger.debug(message, *args, **kwargs)

    def info(self, message, *args, **kwargs):
        self._logger.info(message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        self._logger.warning(message, *args, **kwargs)
        self._save_log_to_db('WARNING', message)

    def error(self, error, *args, **kwargs):
        msg = str(error)
        self._logger.error(msg, *args, **kwargs)
        self._save_log_to_db('ERROR', msg)
        self._save_log_to_botcity(error)

    def exception(self, message, *args, **kwargs):
        self._logger.exception(message, *args, **kwargs)
        tb_info = traceback.format_exc()
        self._save_log_to_db('EXCEPTION', f'{message}\n{tb_info}')

    def critical(self, message, *args, **kwargs):
        self._logger.critical(message, *args, **kwargs)
        self._save_log_to_db('CRITICAL', message)

    def _save_log_to_botcity(self, exception):
        if self._local_execution:
            return
        if not isinstance(exception, Exception):
            return
        self.maestro.error(task_id=self.maestro.task_id, exception=exception)

    def _save_log_to_db(self, level: str, message: str):
        pass
