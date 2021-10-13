import pytest

from cumulusci.core.versions import PackageVersionNumber, VersionTypeEnum


class TestPackageVersionNumber:
    def test_parse_format(self):
        assert PackageVersionNumber.parse("1.2.3.4").format() == "1.2.3.4"
        assert PackageVersionNumber.parse("1.2.3 (Beta 4)").format() == "1.2.3 (Beta 4)"
        assert PackageVersionNumber.parse("1.2.3").format() == "1.2.3"

        assert (
            PackageVersionNumber.parse_tag(
                "release/1.2.3", "release/", "beta/"
            ).format()
            == "1.2.3"
        )
        assert (
            PackageVersionNumber.parse_tag(
                "beta/1.2.3-Beta_4", "release/", "beta/"
            ).format()
            == "1.2.3 (Beta 4)"
        )
        assert (
            PackageVersionNumber.parse_tag("beta/1.2.3.4", "release/", "beta/").format()
            == "1.2.3.4"
        )

    def test_parse__invalid(self):
        with pytest.raises(ValueError):
            PackageVersionNumber.parse("asdf")

    def test_increment(self):
        assert (
            PackageVersionNumber.parse("1.0").increment(VersionTypeEnum.major).format()
            == "2.0.0.NEXT"
        )
        assert (
            PackageVersionNumber.parse("1.0").increment(VersionTypeEnum.minor).format()
            == "1.1.0.NEXT"
        )
        assert (
            PackageVersionNumber.parse("1.0").increment(VersionTypeEnum.patch).format()
            == "1.0.1.NEXT"
        )
