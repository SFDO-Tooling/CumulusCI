from cumulusci.utils.org_schema_models import SObject


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
