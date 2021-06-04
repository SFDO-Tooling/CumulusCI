import unittest
from unittest import mock
from pathlib import Path
import tempfile
import shutil
import os
import json

from cumulusci.robotframework.utam import UTAM


class TestUTAM(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempdir = Path(tempfile.mkdtemp())
        utam_def = {
            "root": True,
            "selector": {"css": "body"},
            "elements": [
                {"name": "header", "selector": {"css": "div.header"}, "public": True},
                {"name": "footer", "selector": {"css": "div.footer"}, "public": True},
                {
                    "name": "body",
                    "selector": {"css": "div.body"},
                    "public": False,
                    "elements": [
                        {"name": "nav", "selector": {"css": "div.nav"}, "public": True}
                    ],
                },
            ],
        }
        with open(cls.tempdir / "test-object.utam.json", "w") as f:
            print(f"creating {f.name}")
            json.dump(utam_def, f)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tempdir)

    def test_cannot_find_file(self):
        """Verify we can instantiate a utam page object from UTAMPATH env var"""
        with self.assertRaisesRegex(
            Exception, "page object for 'bogus-object' not found."
        ):
            UTAM("bogus-object")

    def test_smoke(self):
        """Verify we can load a utam object when it's in UTAMPATH"""
        with mock.patch.dict(os.environ, {"UTAMPATH": str(self.tempdir)}):
            UTAM("test-object")

    def test_getters(self):
        """Verify getters are created for all public elements"""
        with mock.patch.dict(os.environ, {"UTAMPATH": str(self.tempdir)}):
            po = UTAM("test-object")
            # this will break if we add any other methods that begin with "get"...
            getters = [
                method_name for method_name in dir(po) if method_name.startswith("get")
            ]
            assert getters == ["getFooter", "getHeader", "getNav"]
