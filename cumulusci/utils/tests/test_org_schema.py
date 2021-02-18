import json
from unittest.mock import patch
from pathlib import Path
from itertools import chain
import gzip

import pytest
import yaml

from sqlalchemy import create_engine

from cumulusci.salesforce_api.org_schema import (
    get_org_schema,
    BufferedSession,
    zip_database,
)
from cumulusci.salesforce_api.org_schema_models import Base


class FakeSF:
    """A pretend version of Salesforce for composite testing"""

    base_url = "https://innovation-page-2420-dev-ed.cs50.my.salesforce.com/"
    headers = {}

    def describe(self):
        return {
            "encoding": "UTF-8",
            "maxBatchSize": 200,
            "sobjects": [
                {"createable": False, "deletable": True, "name": "Account"},
                {"createable": False, "deletable": True, "name": "Contact"},
            ],
        }


def makeFakeCompositeParallelSalesforce(responses):
    class FakeCompositeParallelSalesforce:
        def __init__(self, sf, *args, **kwargs):
            self.sf = sf

        def __enter__(self, *args, **kwargs):
            return self

        def __exit__(self, *args, **kwargs):
            pass

        def do_composite_requests(self, requests):
            return responses()

    return FakeCompositeParallelSalesforce


def uncached_responses(responses):
    """Pretend to load uncached responses from a VCR cassette"""

    def parse_composite_response(interaction: dict):
        response_body = interaction["response"]["body"]["string"]
        struct = json.loads(response_body)
        return struct["compositeResponse"]

    return chain.from_iterable(
        parse_composite_response(interaction)
        for interaction in responses["interactions"]
        if interaction["request"]["uri"].endswith("/composite")
    )


cached_responses = [
    {"body": None, "httpHeaders": {}, "httpStatusCode": 304, "referenceId": "noId"}
] * 4


def mock_return_uncached_responses(cassette_data):
    return patch(
        "cumulusci.salesforce_api.org_schema.CompositeParallelSalesforce",
        makeFakeCompositeParallelSalesforce(lambda: uncached_responses(cassette_data)),
    )


def mock_return_cached_responses():
    return patch(
        "cumulusci.salesforce_api.org_schema.CompositeParallelSalesforce",
        makeFakeCompositeParallelSalesforce(lambda: cached_responses.copy()),
    )


class TestDescribeOrg:
    def setup_class(self):
        cassette = (
            Path(__file__).parent
            / "cassettes/TestDescribeOrg.test_describe_to_sql.yaml"
        )
        with open(cassette) as f:
            self.cassette_data = yaml.safe_load(f)

    def validate_schema_data(self, schema):
        assert len(list(schema.sobjects)) == 4
        assert schema["Account"].createable is True
        assert schema["Account"].fields["Id"].aggregatable is True
        assert schema["Account"].labelPlural == "Accounts"
        account_desc = schema["Account"]
        for name, value in account_data.items():
            if name != "fields":
                assert account_desc[name] == value, (
                    name,
                    value,
                    account_desc[name],
                )
        for field in account_data["fields"]:
            db_field = account_desc["fields"][field["name"]]
            for name, value in field.items():
                assert db_field[name] == value, (
                    name,
                    value,
                    db_field[name],
                )

    def test_describe_to_sql(self, fallback_org_config):
        # Step 1: Pretend to download data from server
        org_config = fallback_org_config()
        with mock_return_uncached_responses(self.cassette_data):
            with get_org_schema(FakeSF(), org_config) as schema:
                self.validate_schema_data(schema)

        # Step 2: Call the server again.
        #         This time it has nothing new to tell us so nothing
        # should be written to the local database except an updated
        # LastModifiedDate.
        with mock_return_cached_responses(), patch(
            "cumulusci.salesforce_api.org_schema.create_row"
        ) as create_row, get_org_schema(FakeSF(), org_config) as schema:
            self.validate_schema_data(schema)
            for call in create_row.mock_calls:
                assert call[1][1].__name__ == "FileMetadata"

    def test_errors(self, org_config):
        with mock_return_uncached_responses(self.cassette_data), get_org_schema(
            FakeSF(), org_config
        ) as schema:
            with pytest.raises(KeyError):
                schema["Foo"]

    def test_forced_recache(self, org_config):
        with mock_return_uncached_responses(self.cassette_data):
            with get_org_schema(FakeSF(), org_config) as schema:
                schema.session.execute("insert into sobjects (name) values ('Foo')")
                assert "Foo" in schema
                schema.session._real_commit__()
                dbpath = schema.engine.url.translate_connect_args()["database"]
                zip_database(Path(dbpath), schema.path)
            with get_org_schema(FakeSF(), org_config) as schema:
                assert "Foo" in schema
            with get_org_schema(FakeSF(), org_config, force_recache=True) as schema:
                assert "Foo" not in schema

    def test_dict_like(self, org_config):
        with mock_return_uncached_responses(self.cassette_data):
            with get_org_schema(FakeSF(), org_config) as schema:
                assert schema["Account"]
                assert "Account" in schema
                assert sorted(schema.keys())[0] == "Account"
                assert (
                    sorted(schema.values(), key=lambda x: x.name)[0].name == "Account"
                )
                a, b = sorted(schema.items())[0]
                assert a == "Account"
                assert "Account" in schema.keys()
                assert "<Schema" in repr(schema)

    def test_misuse(self, org_config):
        """What if the user keeps a reference to the schema"""
        with mock_return_uncached_responses(self.cassette_data):
            with get_org_schema(FakeSF(), org_config) as schema:
                pass
        with pytest.raises(IOError):
            schema.session.commit()

    def test_corrupted_schema(self, caplog, org_config):
        "What if the schema GZip is corrupted?"
        with mock_return_uncached_responses(self.cassette_data):
            with get_org_schema(FakeSF(), org_config) as schema:
                assert "Account" in schema
                path = schema.path
            assert not caplog.text
            with open(path, "w") as p:
                p.write("xxx")

            with get_org_schema(FakeSF(), org_config) as schema:
                assert "Account" in schema
            assert caplog.text

    def test_corrupted_schema__sqlite(self, caplog, org_config):
        "What if the schema inside the gzip is corrupted"
        with mock_return_uncached_responses(self.cassette_data):
            with get_org_schema(FakeSF(), org_config) as schema:
                assert "Account" in schema
                path = schema.path
            assert not caplog.text
            with open(path, "wb") as p:
                with gzip.GzipFile(fileobj=p) as gzipped:
                    gzipped.write(b"xxx")

            with get_org_schema(FakeSF(), org_config) as schema:
                assert "Account" in schema
            assert caplog.text


@pytest.mark.no_vcr()  # too hard to make these VCR-compatible due to data volume
@pytest.mark.integration_test()
class TestOrgSchemaIntegration:
    def validate_real_schema_data(self, schema):
        assert len(list(schema.sobjects)) > 800
        assert schema["Account"].createable is True
        assert schema["Account"].fields["Id"].aggregatable is True
        assert schema["Account"].labelPlural == "Accounts"
        account_desc = schema["Account"]
        assert account_desc.deletable is True
        assert account_desc.undeletable is True
        assert account_desc.keyPrefix == "001"

    def test_cache_schema(self, sf, org_config):
        with get_org_schema(sf, org_config, force_recache=True) as schema:
            self.validate_real_schema_data(schema)
            assert not schema.from_cache
        with get_org_schema(sf, org_config) as schema:
            self.validate_real_schema_data(schema)
            assert schema.from_cache


class TestBufferedSession:
    def test_buffer_empties(self):
        engine = create_engine("sqlite:///")
        Base.metadata.bind = engine
        Base.metadata.create_all()
        bs = BufferedSession(engine, Base.metadata, 5)
        with patch.object(bs, "flush") as flush:
            for i in range(0, 3):
                bs.write_single_row("sobjects", {"name": str(i)})
            assert not flush.mock_calls
            for i in range(0, 3):
                bs.write_single_row("sobjects", {"name": str(i)})

        assert flush.mock_calls


account_data = {
    "actionOverrides": (),
    "activateable": False,
    "compactLayoutable": True,
    "createable": True,
    "custom": False,
    "customSetting": False,
    "deepCloneable": False,
    "defaultImplementation": None,
    "deletable": True,
    "deprecatedAndHidden": False,
    "extendedBy": None,
    "extendsInterfaces": None,
    "feedEnabled": True,
    "fields": [
        {
            "aggregatable": True,
            "aiPredictionField": False,
            "autoNumber": False,
            "byteLength": 18,
            "calculated": False,
            "calculatedFormula": None,
            "cascadeDelete": False,
            "caseSensitive": False,
            "compoundFieldName": None,
            "controllerName": None,
            "createable": False,
            "custom": False,
            "defaultValue": None,
            "defaultValueFormula": None,
            "defaultedOnCreate": True,
            "dependentPicklist": False,
            "deprecatedAndHidden": False,
            "digits": 0,
            "displayLocationInDecimal": False,
            "encrypted": False,
            "externalId": False,
            "extraTypeInfo": None,
            "filterable": True,
            "filteredLookupInfo": None,
            "formulaTreatNullNumberAsZero": False,
            "groupable": True,
            "highScaleNumber": False,
            "htmlFormatted": False,
            "idLookup": True,
            "inlineHelpText": None,
            "label": "Account ID",
            "length": 18,
            "mask": None,
            "maskType": None,
            "name": "Id",
            "nameField": False,
            "namePointing": False,
            "nillable": False,
            "permissionable": False,
            "picklistValues": [],
            "polymorphicForeignKey": False,
            "precision": 0,
            "queryByDistance": False,
            "referenceTargetField": None,
            "referenceTo": [],
            "relationshipName": None,
            "relationshipOrder": None,
            "restrictedDelete": False,
            "restrictedPicklist": False,
            "scale": 0,
            "searchPrefilterable": False,
            "soapType": "tns:ID",
            "sortable": True,
            "type": "id",
            "unique": False,
            "updateable": False,
            "writeRequiresMasterRead": False,
        }
    ],
    "hasSubtypes": False,
    "implementedBy": None,
    "implementsInterfaces": None,
    "isInterface": False,
    "isSubtype": False,
    "keyPrefix": "001",
    "label": "Account",
    "labelPlural": "Accounts",
    "layoutable": True,
    "listviewable": None,
    "lookupLayoutable": None,
    "mergeable": True,
    "mruEnabled": True,
    "name": "Account",
    "namedLayoutInfos": (),
    "networkScopeFieldName": None,
    "queryable": True,
    "replicateable": True,
    "retrieveable": True,
    "searchLayoutable": True,
    "searchable": True,
    "sobjectDescribeOption": "FULL",
    "triggerable": True,
    "undeletable": True,
    "updateable": True,
    "urls": {"a": "b"},
}


## These are helper functions for managing the sample data used above.
## The functions aren't called above, but test maintainers could use
## them to update sample data.


def reduce_data(filename):
    """A function for reducing Casettes of Describes() to the bare minimum

    Note that the deep_describe infrastructure uses threads and may not
    always play nicely with vcr. It may take some experimentation and cutting
    and pasting to get a decent vcr cassette to use as the input of this
    function."""
    relevant_objs = ["Account", "Contact", "Opportunity", "Campaign"]
    data = yaml.safe_load(open(filename))

    for interaction in data["interactions"]:
        url = interaction["request"].get("uri")
        if url and url.endswith("composite"):
            reduce_composite(interaction)
        elif url:
            assert url.endswith("sobjects"), url
            reduce_describe(interaction, relevant_objs)

    yaml.safe_dump(data, open(filename + ".out.yaml", "w"))


def reduce_composite(interaction):
    results = json.loads(interaction["response"]["body"]["string"])["compositeResponse"]
    sobjs = [result["body"] for result in results]
    for sobj in sobjs:
        sobj["fields"] = sobj["fields"][0:1]
        for key in ["urls", "childRelationships", "recordTypeInfos", "supportedScopes"]:
            if sobj.get(key):
                del sobj[key]

    interaction["response"]["body"]["string"] = json.dumps(
        {"compositeResponse": results}
    )


def reduce_describe(interaction, relevant_objs):
    sobjs = json.loads(interaction["response"]["body"]["string"])["sobjects"]
    results = []
    for sobj in sobjs:
        if sobj["name"] not in relevant_objs:
            continue
        for key in ["urls", "childRelationships", "recordTypeInfos", "supportedScopes"]:
            if sobj.get(key):
                del sobj[key]
        results.append(sobj)

    interaction["response"]["body"]["string"] = json.dumps({"sobjects": results})
