from DataGenerator import Context

from sqlalchemy import MetaData, create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import create_session

from cumulusci.tasks.bulkdata.utils import create_table


class OutputStream:
    def output_batches(self, factories, number, variables):
        context = Context(None, None, self, variables)
        for i in range(0, number):
            for factory in factories:
                self.output(factory, context)

    def output(self, factory, context):
        return factory.generate_rows(self, context)

    def write_row(self, tablename, row):
        assert 0, "Not implemented"


class DebugOutputEngine(OutputStream):
    def write_row(self, tablename, row):
        print(tablename, row)


class SqlOutputEngine(OutputStream):
    def __init__(self, db_url, mappings):
        self.init_db(db_url, mappings)

    def init_db(self, db_url, mappings):
        self.engine = engine = create_engine(db_url)
        self.metadata = metadata = MetaData()
        metadata.bind = engine
        for mapping in mappings.values():
            print(mapping)
            create_table(mapping, metadata)

        metadata.create_all()
        self.base = automap_base(bind=engine, metadata=metadata)
        self.base.prepare(engine, reflect=True)
        self.session = create_session(bind=engine, autocommit=False)
        return self.session, self.engine, self.base

    def write_row(self, tablename, row):
        #  TODO: use sessions properly
        model = self.metadata.tables[tablename]
        ins = model.insert().values(**row)
        self.session.execute(ins)
        self.session.commit()
        print("Inserted", tablename, row)
