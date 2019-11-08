from cumulusci.tasks.bulkdata.base_generate_data_task import BaseGenerateDataTask


class OutputStream:
    def write_row(self, tablename, row):
        assert 0, "Not implemented"


class DebugOutputStream(OutputStream):
    def write_row(self, tablename, row):
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

    def write_row(self, tablename, row):
        #  TODO: use sessions properly
        print(self.metadata.tables)
        model = self.metadata.tables[tablename]
        ins = model.insert().values(**row)
        self.session.execute(ins)
        self.session.commit()
