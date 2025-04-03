import re
from typing import Optional, Union

from pydantic.v1 import BaseModel

from cumulusci.core.enums import StrEnum

VERSION_RE = re.compile(
    r"^(?P<MajorVersion>\d+)"
    r".(?P<MinorVersion>\d+)"
    r"(\.(?P<PatchVersion>\d+))?"
    r"(\.(?P<BuildNumber>\d+))?"
    r"(( \([bB]eta (?P<BetaNumber>\d+)\))?$|(-Beta_(?P<BetaNumberTag>\d+))?$)"
)


class VersionTypeEnum(StrEnum):
    major = "major"
    minor = "minor"
    patch = "patch"
    build = "build"


class PackageType(StrEnum):
    FIRST_GEN = "1GP"
    SECOND_GEN = "2GP"


class PackageVersionNumber(BaseModel):
    """A Salesforce package version parsed into components,
    that knows how to format itself for user presentation and for tag names."""

    MajorVersion: int = 0
    MinorVersion: int = 0
    PatchVersion: int = 0
    BuildNumber: Union[int, str] = 0
    IsReleased: bool = False

    package_type: PackageType = PackageType.SECOND_GEN

    def format_tag(self, prefix: str) -> str:
        """Format version number as a tag name."""
        return (
            f"{prefix}{self.format()}".replace(" (", "-")
            .replace(")", "")
            .replace(" ", "_")
        )

    def __str__(self):
        return self.format()

    def format(self):
        if self.package_type is PackageType.FIRST_GEN:
            return self.format_1gp()
        else:
            return self.format_2gp()

    def format_2gp(self) -> str:
        """Format version number as a string for 2GP packages"""
        return f"{self.MajorVersion}.{self.MinorVersion}.{self.PatchVersion}.{self.BuildNumber}"

    def format_1gp(self) -> str:
        """Format version number as a string for 1GP packages"""
        patch = f".{self.PatchVersion}" if self.PatchVersion else ""
        beta = f" (Beta {self.BuildNumber})" if self.BuildNumber else ""

        return f"{self.MajorVersion}.{self.MinorVersion}{patch}{beta}"

    @classmethod
    def parse_tag(
        cls,
        s: str,
        prefix_beta: str,
        prefix_prod: str,
        package_type: Optional[PackageType] = None,
    ) -> "PackageVersionNumber":
        if s.startswith(prefix_beta):
            version = s[len(prefix_beta) :]
        elif s.startswith(prefix_prod):
            version = s[len(prefix_prod) :]
        else:
            version = s
        return cls.parse(
            version,
            is_released=s.startswith(prefix_prod),
            package_type=package_type,
        )

    @classmethod
    def parse(
        cls,
        s: str,
        is_released: Optional[bool] = None,
        package_type: Optional[PackageType] = None,
    ) -> "PackageVersionNumber":
        """Parse a version number from a string"""
        match = VERSION_RE.match(s)
        if not match:
            raise ValueError(f"Could not parse version number: {s}")

        first_gen_beta = bool(match.group("BetaNumber") or match.group("BetaNumberTag"))
        build_number = int(
            match.group("BuildNumber")
            or match.group("BetaNumber")
            or match.group("BetaNumberTag")
            or 0
        )
        if package_type is None:
            # .0 is rare, but legal, for a 2GP
            if first_gen_beta or not match.group("BuildNumber"):
                package_type = PackageType.FIRST_GEN
            else:
                package_type = PackageType.SECOND_GEN

        if is_released is None:
            is_released = not first_gen_beta

        return PackageVersionNumber(
            MajorVersion=int(match.group("MajorVersion")),
            MinorVersion=int(match.group("MinorVersion")),
            PatchVersion=int(match.group("PatchVersion") or 0),
            BuildNumber=build_number,
            IsReleased=is_released,
            package_type=package_type,
        )

    def increment(self, version_type: VersionTypeEnum = VersionTypeEnum.build):
        """Construct a new PackageVersionNumber by incrementing the specified component."""
        if self.package_type is not PackageType.SECOND_GEN:
            raise ValueError("Cannot increment the version number of a 1GP package")

        parts = self.dict()
        parts["BuildNumber"] = "NEXT"
        parts["IsReleased"] = False

        if version_type == VersionTypeEnum.major:
            parts["MajorVersion"] += 1
            parts["MinorVersion"] = 0
            parts["PatchVersion"] = 0
        if version_type == VersionTypeEnum.minor:
            parts["MinorVersion"] += 1
            parts["PatchVersion"] = 0
        elif version_type == VersionTypeEnum.patch:
            parts["PatchVersion"] += 1

        return PackageVersionNumber(**parts)


PackageVersionNumber.update_forward_refs()
