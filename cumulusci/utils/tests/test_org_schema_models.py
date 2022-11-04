import pytest

from cumulusci.salesforce_api.org_schema_models import SObject


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

    def test_roundtrip_mappings(self, temp_db):
        with temp_db() as (connection, metadata, session):
            session.add(SObject(name="Foo", urls={"a": "b"}))
            session.commit()
        with temp_db() as (connection, metadata, session):
            foo = session.query(SObject).one()
            assert foo["name"] == "Foo"
            assert foo["urls"] == {"a": "b"}

    def test_roundtrip_mappings__empty(self, temp_db):
        # with temp_db() as open_db:
        with temp_db() as (connection, metadata, session):
            session.add(SObject(name="Foo", urls={}))
            session.commit()
        with temp_db() as (connection, metadata, session):
            foo = session.query(SObject).one()
            assert foo["name"] == "Foo"
            assert foo["urls"] == {}
            assert session.execute("select urls from sobjects").first()["urls"] is None

    def test_roundtrip_sequences(self, temp_db):
        # with temp_db() as open_db:
        with temp_db() as (connection, metadata, session):
            session.add(
                SObject(name="Foo", childRelationships=[("a", "b"), ("c", "d")])
            )
            session.commit()
        with temp_db() as (connection, metadata, session):
            foo = session.query(SObject).one()
            assert foo["name"] == "Foo"
            assert foo["childRelationships"] == (("a", "b"), ("c", "d"))

    def test_roundtrip_sequences__empty(self, temp_db):
        with temp_db() as (connection, metadata, session):
            session.add(SObject(name="Foo", childRelationships=[]))
            session.commit()
        with temp_db() as (connection, metadata, session):
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
