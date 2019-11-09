from cumulusci.tasks.bulkdata.base_generate_data_task import BaseGenerateDataTask
from abc import abstractmethod, ABC


class OutputStream(ABC):
    count = 0

    def __init__(self):
        self.count += 1

    def write_row(self, tablename, row):
        self.write_single_row(tablename, row)
        if self.count > 1000:
            self.flush()
            self.count = 0

    @abstractmethod
    def write_single_row(self, tablename, row):
        pass


class DebugOutputStream(OutputStream):
    def write_single_row(self, tablename, row):
        print(tablename, row)


class SqlOutputStream(OutputStream):
    def __init__(self, session, engine, base):
        self.session = session
        self.engine = engine
        self.base = base
        self.metadata = base.metadata
        self.metadata.bind = self.engine

    @classmethod
    def from_url(cls, db_url, mappings):
        return cls.from_open_connection(*BaseGenerateDataTask.init_db(db_url, mappings))

    def write_single_row(self, tablename, row):
        #  TODO: use sessions properly
        model = self.metadata.tables[tablename]
        ins = model.insert().values(**row)
        self.session.execute(ins)

    def flush(self):
        self.session.flush()
