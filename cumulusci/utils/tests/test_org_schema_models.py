from tempfile import TemporaryDirectory
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from cumulusci.utils.org_schema_models import Base, SObject


class TestOrgSchemaModels:
    def test_sobject__eq__true(self):
        a = SObject(name="foo", createable=False)
        b = SObject(name="foo", createable=False)
        assert a == b

    def test_sobject__eq__false(self):
        a = SObject(name="foo", createable=False)
        b = SObject(name="bar", createable=False)
        assert a != b
        b = SObject(name="bar", createable=True)
        assert a != b

    def test_repr(self):
        a = SObject(name="foo", createable=False)
        r = repr(a)
        assert "foo" in r
        assert "createable" in r

    @contextmanager
    def temp_db(self):
        with TemporaryDirectory() as t:

            @contextmanager
            def open_db():
                engine = create_engine(f"sqlite:///{t}/tempfile.db")
                with engine.connect() as connection:
                    Session = sessionmaker(bind=connection)
                    Base.metadata.bind = engine
                    Base.metadata.create_all()
                    session = Session()
                    yield connection, Base.metadata, session

            yield open_db

    def test_roundtrip_mappings(self):
        with self.temp_db() as open_db:
            with open_db() as (connection, metadata, session):
                session.add(SObject(name="Foo", urls={"a": "b"}))
                session.commit()
            with open_db() as (connection, metadata, session):
                foo = session.query(SObject).one()
                assert foo["name"] == "Foo"
                assert foo["urls"] == {"a": "b"}

    def test_roundtrip_mappings__empty(self):
        with self.temp_db() as open_db:
            with open_db() as (connection, metadata, session):
                session.add(SObject(name="Foo", urls={}))
                session.commit()
            with open_db() as (connection, metadata, session):
                foo = session.query(SObject).one()
                assert foo["name"] == "Foo"
                assert foo["urls"] == {}
                assert (
                    session.execute("select urls from sobjects").first()["urls"] is None
                )

    def test_roundtrip_sequences(self):
        with self.temp_db() as open_db:
            with open_db() as (connection, metadata, session):
                session.add(
                    SObject(name="Foo", childRelationships=[("a", "b"), ("c", "d")])
                )
                session.commit()
            with open_db() as (connection, metadata, session):
                foo = session.query(SObject).one()
                assert foo["name"] == "Foo"
                assert foo["childRelationships"] == (("a", "b"), ("c", "d"))

    def test_roundtrip_sequences__empty(self):
        with self.temp_db() as open_db:
            with open_db() as (connection, metadata, session):
                session.add(SObject(name="Foo", childRelationships=[]))
                session.commit()
            with open_db() as (connection, metadata, session):
                foo = session.query(SObject).one()
                assert foo["name"] == "Foo"
                assert foo["childRelationships"] == ()
                assert (
                    session.execute("select childRelationships from sobjects").first()[
                        "childRelationships"
                    ]
                    is None
                )

    def test_getattr_getitem(self):
        so = SObject(name="Foo", childRelationships=[])
        assert so.name == so["name"]
        with pytest.raises(KeyError):
            so["aaa"]

        with pytest.raises(AttributeError):
            so.aaa
