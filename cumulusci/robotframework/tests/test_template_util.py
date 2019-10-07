import unittest
from cumulusci.robotframework import template_utils


class TemplateUtils(unittest.TestCase):
    def test_string_generator(self):
        x = 100
        y = template_utils.StringGenerator(lambda: str(x))
        assert str(y) == "100"
        x = 200
        assert str(y) == "200"

    def test_faker_library(self):
        fake = template_utils.FakerTemplateLibrary()
        assert fake.first_name
        assert fake.email(domain="salesforce.com")
