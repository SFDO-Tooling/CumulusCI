import unittest
from cumulusci.core import template_utils


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

    def test_format_str(self):
        assert template_utils.format_str("abc") == "abc"
        assert template_utils.format_str("{{abc}}", abc=5) == "5"
        assert len(template_utils.format_str("{{fake.first_name}}"))
        assert "15" in template_utils.format_str(
            "{{fake.first_name}} {{count}}", count=15
        )
        assert "15" in template_utils.format_str(
            "{{fake.first_name}} {{count}}", count="15"
        )
        assert template_utils.format_str("{% raw %}{}{% endraw %}", count="15") == "{}"
