import pytest

from cumulusci.core.versions import PackageType, PackageVersionNumber, VersionTypeEnum


class TestPackageVersionNumber:
    def test_parse_format(self):
        assert PackageVersionNumber.parse("1.2.3.4").format() == "1.2.3.4"
        assert (
            str(
                PackageVersionNumber.parse(
                    "1.2.3.4", package_type=PackageType.FIRST_GEN
                )
            )
            == "1.2.3 (Beta 4)"
        )
        assert PackageVersionNumber.parse("1.2.3 (Beta 4)").format() == "1.2.3 (Beta 4)"
        assert PackageVersionNumber.parse("1.2.3 (beta 4)").format() == "1.2.3 (Beta 4)"
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
        assert (
            PackageVersionNumber.parse_tag(
                "beta/1.2.3.4", "release/", "beta/"
            ).format_tag("beta/")
            == "beta/1.2.3.4"
        )
        assert (
            PackageVersionNumber.parse_tag(
                "beta/1.2.3-Beta_4", "release/", "beta/"
            ).format_tag("beta/")
            == "beta/1.2.3-Beta_4"
        )

    def test_parse__invalid(self):
        with pytest.raises(ValueError):
            PackageVersionNumber.parse("asdf")

    def test_increment(self):
        assert (
            PackageVersionNumber.parse("1.0.0.1")
            .increment(VersionTypeEnum.major)
            .format()
            == "2.0.0.NEXT"
        )
        assert (
            PackageVersionNumber.parse("1.0.0.1")
            .increment(VersionTypeEnum.minor)
            .format()
            == "1.1.0.NEXT"
        )
        assert (
            PackageVersionNumber.parse("1.0.0.1")
            .increment(VersionTypeEnum.patch)
            .format()
            == "1.0.1.NEXT"
        )

    def test_increment__1gp(self):
        with pytest.raises(ValueError):
            PackageVersionNumber.parse("1.0 (Beta 4)").increment(VersionTypeEnum.major)
