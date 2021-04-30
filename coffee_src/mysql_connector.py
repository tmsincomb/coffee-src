from typing import Tuple, List

import pandas as pd
from sqlalchemy import create_engine, inspect, exc


class MysqlConnector:

    def __init__(self, app=None, db_url=None):
        if not db_url:
            db_url = open('.mypass').read()
        self.engine = create_engine(db_url)

    def get(self, query: str) -> Tuple[int, pd.DataFrame]:
        """
        Query MySQL database

        Parameters
        ----------
        query : str
            Raw select MySQL string

        Returns
        -------
        Tuple[int, pd.DataFrame]
            Response Code, Pandas DataFrame
        """
        try:
            df = pd.read_sql(query, self.engine)
            return 1, df
        except exc.SQLAlchemyError as e:
            return 0, e

    def post(self, command: str) -> Tuple[int, str]:
        """
        Modify MySQL database

        Parameters
        ----------
        command : str
            raw update/delete MySQL string

        Returns
        -------
        Tuple[int, str]
            Response Code, Response 
        """
        connection = self.engine.connect()
        trans = connection.begin()
        try:
            resp = connection.execute(command)
            trans.commit()
            connection.close()
            return 1, resp
        except exc.SQLAlchemyError as e:
            trans.rollback()
            connection.close()
            return 0, e

    def descibe_database(self) -> List[Tuple[str, pd.DataFrame]]:
        """
        Reveals Database Schema

        Returns
        -------
        List[Tuple[str, pd.DataFrame]]
            A list of the table names with their dataframe table
        """
        inspector = inspect(self.engine)
        database = []
        for tablename in inspector.get_table_names():
            table = pd.DataFrame(inspector.get_columns(tablename))
            database.append((tablename, table))
        return database

    def get_table(self, tablename: str) -> pd.DataFrame:
        """
        Get Pandas DataFrame rep of MySQL table.

        Parameters
        ----------
        tablename : str
            MySQL database table name

        Returns
        -------
        pd.DataFrame
            complete MySQL table
        """
        inspector = inspect(self.engine)
        return pd.DataFrame(inspector.get_columns(tablename))

    def update_table(self, table: pd.DataFrame, tablename: str) -> str:
        """
        Takes a frame and updates the table identified with it for a robust bulk update.t

        Parameters
        ----------
        table : pd.DataFrame
            rows to update in their correct type and values of
        tablename : str
            table name in the MySQL database to update with said frame

        Returns
        -------
        str
            MySQL raw response.
        """
        resp = table.to_sql(tablename, self.engine, if_exists="replace")
        return resp
