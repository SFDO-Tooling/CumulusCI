from cumulusci.core import template_utils


class TestTemplateUtils:
    def test_string_generator(self):
        x = 100
        y = template_utils.StringGenerator(lambda: str(x))
        assert str(y) == "100"
        x = 200
        assert str(y) == "200"

    def test_faker_library(self):
        fake = template_utils.FakerTemplateLibrary()
        assert fake.first_name
        assert "example.com" in fake.email(domain="example.com")

    def test_faker_languages(self):
        fake = template_utils.FakerTemplateLibrary("no_NO")
        assert fake.first_name
        assert "example.com" in fake.email(domain="example.com")

    def test_format_str(self):
        assert template_utils.format_str("abc") == "abc"
        assert template_utils.format_str("{{abc}}", {"abc": 5}) == "5"
        assert len(template_utils.format_str("{{fake.first_name}}"))
        assert "15" in template_utils.format_str(
            "{{fake.first_name}} {{count}}", {"count": 15}
        )
        assert "15" in template_utils.format_str(
            "{{fake.first_name}} {{count}}", {"count": "15"}
        )
        assert (
            template_utils.format_str("{% raw %}{}{% endraw %}", {"count": "15"})
            == "{}"
        )

    def test_format_str_languages(self):
        norwegian_faker = template_utils.FakerTemplateLibrary("no_NO")

        val = template_utils.format_str(
            "{{vikingfake.first_name}} {{abc}}",
            {"abc": 5, "vikingfake": norwegian_faker},
        )
        assert "5" in val

        def cosmopolitan_faker(language):
            return template_utils.FakerTemplateLibrary(language)

        val = template_utils.format_str(
            "{{fakei18n('ne_NP').first_name}} {{abc}}",
            {"abc": 5, "fakei18n": cosmopolitan_faker, "type": type},
        )
        assert "5" in val
