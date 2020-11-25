import pathlib

import pytest

from cumulusci.core.exceptions import CumulusCIException
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


def class_md():
    cls = MetadataElement("ApexClass")
    return cls


def write_metadata(tree: MetadataElement, path: pathlib.Path, subpath: str):
    path = path / subpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tree.tostring())


class TestMetadataProcessor:
    def test_collect_members(self, src):
        # object with field
        write_metadata(object_with_field_md(), src, "objects/Test__c.object")
        # field only
        md = object_with_field_md()
        md.remove(md.label)
        write_metadata(md, src, "objects/___NAMESPACE___Other__c.object")
        # extra files that should not be collected
        (src / "objects" / ".DS_Store").write_text("")
        (src / "objects" / "bogus").write_text("")

        pkg = MetadataPackage.from_path(src)
        assert pkg.types == {
            "CustomObject": ["Test__c"],
            "CustomField": [
                "Test__c.Favorite_Color__c",
                "%%%NAMESPACE%%%Other__c.Favorite_Color__c",
            ],
        }

    def test_collect_members__unknown(self, src):
        (src / "bogus").mkdir()
        with pytest.raises(CumulusCIException):
            MetadataPackage.from_path(src)

    def test_merge__adds_object(self, src, dest):
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

    def test_merge__ignores_dotfiles(self, src, dest):
        (src / "objects").mkdir()
        (src / "objects" / ".DS_Store").write_text("")
        merge_metadata(src, dest)
        assert not (dest / "DS_Store").exists()

    def test_merge__copies_content(self, src, dest):
        # files which are not metadata XML should be copied as is
        write_metadata(class_md(), src, "classes/Test.cls-meta.xml")
        code = "System.debug('');"
        (src / "classes" / "Test.cls").write_text(code)
        merge_metadata(src, dest)
        assert (dest / "classes" / "Test.cls").read_text() == code

    def test_merge_additional_only(self, src, dest):
        rule = MetadataElement("matchingRules")
        rule.append("fullName", "Test")
        body = MetadataElement("MatchingRules")
        body.append(rule)
        write_metadata(body, src, "matchingRules/Contact.matchingRule")
        merge_metadata(src, dest)

        pkg = MetadataPackage.from_path(dest)
        assert pkg.types == {"MatchingRule": ["Contact.Test"]}


class TestFolderMetadataProcessor:
    def test_collect_members(self, src):
        (src / "reports").mkdir()
        (src / "reports" / "CustomReports-meta.xml").write_text("")
        (src / "reports" / "CustomReports").mkdir()
        (src / "reports" / "CustomReports" / "FancyReport.report").write_text("")
        (src / "reports" / "CustomReports" / "bogus").write_text("")

        pkg = MetadataPackage.from_path(src)
        assert pkg.types == {"Report": ["CustomReports", "CustomReports/FancyReport"]}

    def test_merge_report(self, src, dest):
        (src / "reports").mkdir()
        (src / "reports" / "CustomReports-meta.xml").write_text("")
        (src / "reports" / "CustomReports").mkdir()
        (src / "reports" / "CustomReports" / "FancyReport.report").write_text("")
        merge_metadata(src, dest)

        assert (dest / "reports" / "CustomReports-meta.xml").exists()
        assert (dest / "reports" / "CustomReports" / "FancyReport.report").exists()

    def test_merge_document(self, src, dest):
        # documents are a bit odd because they can have any extension,
        # and also have a corresponding -meta.xml file
        (src / "documents").mkdir()
        (src / "documents" / "Images").mkdir()
        (src / "documents" / "Images" / "example.png").write_text("")
        (src / "documents" / "Images" / "example.png-meta.xml").write_text("")
        merge_metadata(src, dest)

        assert (dest / "documents" / "Images" / "example.png").exists()
        assert (dest / "documents" / "Images" / "example.png-meta.xml").exists()


class TestBundleMetadataProcessor:
    def test_collect_members(self, src):
        (src / "lwc" / "Bundle").mkdir(parents=True)
        (src / "lwc" / "README.md").write_text("")
        pkg = MetadataPackage.from_path(src)
        assert pkg.types == {"LightningComponentBundle": ["Bundle"]}

    def test_merge(self, src, dest):
        (dest / "lwc" / "Bundle").mkdir(parents=True)
        (dest / "lwc" / "Bundle" / "test1.js").write_text("")
        # the entire bundle should get overwritten
        (src / "lwc" / "Bundle").mkdir(parents=True)
        (src / "lwc" / "Bundle" / "test2.js").write_text("")
        merge_metadata(src, dest)
        assert not (dest / "lwc" / "Bundle" / "test1.js").exists()
        assert (dest / "lwc" / "Bundle" / "test2.js").exists()
