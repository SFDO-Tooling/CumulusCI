import pathlib

import pytest

from cumulusci.utils import temporary_dir
from cumulusci.utils.metadata import merge_metadata
from cumulusci.utils.metadata import MetadataPackage
from cumulusci.utils.xml.metadata_tree import MetadataElement, parse


@pytest.fixture
def src():
    with temporary_dir(chdir=False) as path:
        yield pathlib.Path(path)


@pytest.fixture
def dest():
    with temporary_dir(chdir=False) as path:
        yield pathlib.Path(path)


def object_md():
    obj = MetadataElement("CustomObject")
    obj.append("label", "Test")
    return obj


def object_with_field_md():
    field = MetadataElement("fields")
    field.append("fullName", "Favorite_Color__c")
    field.append("helpText", "help")
    obj = object_md()
    obj.append(field)
    return obj


def write_metadata(tree: MetadataElement, path: pathlib.Path, subpath: str):
    path = path / subpath
    path.parent.mkdir(parents=True)
    path.write_text(tree.tostring())


class TestObjectMetadataProcessor:
    def test_merge__new_file(self, src, dest):
        # Merge object + field metadata to empty package
        write_metadata(object_with_field_md(), src, "objects/Test__c.object")
        merge_metadata(src, dest)

        # Object + field should be in destination package
        assert (dest / "objects" / "Test__c.object").exists()
        types = MetadataPackage.from_path(dest).types
        assert "Test__c" in types["CustomObject"]
        assert "Test__c.Favorite_Color__c" in types["CustomField"]

    def test_merge__updates_object(self, src, dest):
        # Merge updated object to package where object exists
        write_metadata(object_md(), dest, "objects/Test__c.object")
        obj2 = object_md()
        obj2.label.text = "Test2"
        write_metadata(obj2, src, "objects/Test__c.object")
        merge_metadata(src, dest)

        # Destination should have updated object properties
        md = parse(dest / "objects/Test__c.object")
        labels = md.findall("label")
        assert len(labels) == 1
        assert labels[0].text == "Test2"

    def test_merge__replaces_field(self, src, dest):
        # Merge updated field to package where object exists
        write_metadata(object_with_field_md(), dest, "objects/Test__c.object")
        md = object_with_field_md()
        md.remove(md.label)
        md.fields.helpText.text = "help2"
        write_metadata(md, src, "objects/Test__c.object")
        merge_metadata(src, dest)

        # Destination should have replaced field but retained object properties
        md = parse(dest / "objects/Test__c.object")
        assert md.label.text == "Test"
        assert len(md.findall("fields")) == 1
        assert md.fields.helpText.text == "help2"
