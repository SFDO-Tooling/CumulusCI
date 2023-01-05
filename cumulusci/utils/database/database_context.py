from pathlib import Path
from typing import Mapping

from sqlalchemy import MetaData, create_engine, inspect, select
from sqlalchemy.engine import CursorResult, Engine


class DatabaseContext:
    database_url: str
    engine: Engine

    @classmethod
    def from_database_url(cls, database_url: str):
        self = cls()
        self.database_url = database_url
        self.engine = create_engine(database_url)
        return self

    @classmethod
    def from_sql_file(cls, sql_path: Path):
        self = cls()
        self.engine = create_engine("sqlite:///")

        with self:
            cursor = self.connection.connection.cursor()
            with open(sql_path, "r", encoding="utf-8") as f:
                try:
                    cursor.executescript(f.read())  # type: ignore
                finally:
                    cursor.close()
        return self

    def __enter__(self, *args, **kwargs):
        self.connection = self.engine.connect()
        # initialize the DB session
        self.metadata = MetaData()
        self.metadata.bind = self.connection
        self.inspector = inspect(self.connection)
        self.metadata.reflect()
        return self

    def __exit__(self, *args, **kwargs):
        self.connection.close()

    @property
    def tables(self) -> Mapping:
        return self.metadata.tables

    def rows_for(self, tablename: str) -> CursorResult:
        # table = self.tables[tablename]
        q = select(self.metadata.tables[tablename])
        return self.connection.execute(q)
