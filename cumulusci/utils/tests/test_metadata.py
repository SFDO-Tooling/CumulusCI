# from filecmp import dircmp
import pathlib

import pytest

from cumulusci.utils import temporary_dir
from cumulusci.utils.metadata import MetadataPackage
from cumulusci.utils.xml.metadata_tree import MetadataElement, parse


# def test_manifest():
#     path = pathlib.Path("/Users/dglick/Work/NPSP/src.bak")
#     MetadataPackage(path, version="48.0").write_manifest()
#     copy1 = pathlib.Path("/Users/dglick/Work/NPSP/src/package.xml").read_text()
#     copy2 = pathlib.Path("/Users/dglick/Work/NPSP/src.bak/package.xml").read_text()
#     assert copy2 == copy1


# def test_merge():
#     src_path = pathlib.Path("/Users/dglick/Work/NPSP/src.bak")
#     src = MetadataPackage(src_path)
#     dest_path = pathlib.Path("/Users/dglick/Work/NPSP/src")
#     dest_path.mkdir()
#     dest = MetadataPackage(dest_path, version="48.0")
#     src.merge_to(dest)

#     dircmp(src_path, dest_path).report_full_closure()


def temporary_package():
    with temporary_dir() as path:
        yield MetadataPackage(pathlib.Path(path), version="48.0")


src = pytest.fixture(temporary_package)
dest = pytest.fixture(temporary_package)


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


def write_metadata(tree: MetadataElement, package: MetadataPackage, subpath: str):
    path = package.path / subpath
    path.parent.mkdir(parents=True)
    path.write_text(tree.tostring())


class TestObjectMetadataProcessor:
    def test_merge__new_file(self, src, dest):
        # Merge object + field metadata to empty package
        write_metadata(object_with_field_md(), src, "objects/Test__c.object")
        src.merge_to(dest)

        # Object + field should be in destination package
        assert (dest.path / "objects" / "Test__c.object").exists()
        types = MetadataPackage(dest.path).collect_members()
        assert "Test__c" in types["CustomObject"]
        assert "Test__c.Favorite_Color__c" in types["CustomField"]

    def test_merge__updates_object(self, src, dest):
        # Merge updated object to package where object exists
        write_metadata(object_md(), dest, "objects/Test__c.object")
        obj2 = object_md()
        obj2.label.text = "Test2"
        write_metadata(obj2, src, "objects/Test__c.object")
        src.merge_to(dest)

        # Destination should have updated object properties
        md = parse(dest.path / "objects/Test__c.object")
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
        src.merge_to(dest)

        # Destination should have replaced field but retained object properties
        md = parse(dest.path / "objects/Test__c.object")
        assert md.label.text == "Test"
        assert len(md.findall("fields")) == 1
        assert md.fields.helpText.text == "help2"
