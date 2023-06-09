import sqlite3

import logging
from .dx_exception import DbException

_LOGGER = logging.getLogger(__name__)


class DxDb:
    """
    Handle Db Class
    """

    connection = None

    def __init__(self, url) -> None:
        conn = sqlite3.connect(url)
        _LOGGER.debug("DxDb Init...")
        self.connection = conn
        self._init_table()

    def _init_table(self):
        conn = self.connection
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS gps_logger_history (
		   id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
           entity_id TEXT not NULL,
           longitude REAL not NULL,
		   latitude REAL not null,
		   gcj02_longitude TEXT NULL,
		   gcj02_latitude TEXT null,
           dx_state TEXT null,
           dx_pre_state TEXT null,
           dx_distance INTEGER null,
           dx_record_datetime INTEGER not null
           );"""
            )
            cursor.close()
            conn.commit()
        except Exception as e:
            cursor.close()
            conn.rollback()
            raise DbException("初始化table错误: " + str(e))

    def search(self, sql: str, *args):
        """
        Search SQL

        Parameters:
            sql (str): Sql
            args: Sql Paramters
        """
        conn = self.connection
        try:
            cursor = conn.cursor()
            cursor.execute(sql, args)
            rows = cursor.fetchall()
            column_names = [description[0] for description in cursor.description]
            return_rows = []
            for row in rows:
                return_row = {}
                for i, value in enumerate(row):
                    column_name = column_names[i]
                    return_row[column_name] = value
                return_rows.append(return_row)
            cursor.close()
            return return_rows
        except Exception as e:
            raise DbException("Search 错误: " + str(e))

    def insert(self, sql: str, *args):
        """
        Insert SQL

        Parameters:
            sql (str): Sql
            args: Sql Paramters
        """
        conn = self.connection
        try:
            cursor = conn.cursor()
            cursor.execute(sql, args)
            cursor.close()
            conn.commit()
        except Exception as e:
            raise DbException("Insert 错误: " + str(e))
