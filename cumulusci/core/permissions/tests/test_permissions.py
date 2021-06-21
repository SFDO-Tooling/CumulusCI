import pytest
from cumulusci.core.permissions.permissions import (
    PermissionsUnitFile,
    PermissionsPermSetFile,
    PermissionsProfileFile,
)
from ipaddress import IPv4Address
from io import StringIO
from pydantic import ValidationError


class TestPermissionsUnitYml:
    def test_permissions_unit_yml(self):
        validated = PermissionsUnitFile.parse_from_yaml(
            "cumulusci/core/permissions/tests/test_permissions_unit.yml"
        )
        # Testing a deeply nested value for verification
        assert validated.schema_.defaults["read_all"].object_permissions.create is True

    def test_permissions_unit_yml_error(self):
        with pytest.raises(ValueError):
            validated = PermissionsUnitFile.parse_from_yaml(
                "cumulusci/core/permissions/tests/test_permissions_unit_bad.yml"
            )
            assert (
                validated.schema_.defaults["read_all"].object_permissions.create is True
            )


class TestPermissionsPermSetYml:
    def test_permissions_perm_set_yml(self):
        validated = PermissionsPermSetFile.parse_from_yaml(
            "cumulusci/core/permissions/tests/test_permissions_permset.yml"
        )

        assert validated.label == "Our Permission Set"
        assert validated.license == "None"  # Prolly need to convert to None
        assert validated.activation_required is False
        assert validated.description == "Black holes have hair."

    def test_permissions_profile_yml(self):
        validated = PermissionsProfileFile.parse_from_yaml(
            "cumulusci/core/permissions/tests/test_permissions_profile.yml"
        )

        assert validated.description == "Life is full of surprises."
        assert (
            validated.layouts["Special_Object__c"]["Security"]
            == "Special_Object__c-Admin Layout"
        )
        assert validated.schema_["Payment__c"].delete is False
        assert validated.login_ip_ranges[0].start == IPv4Address("127.0.0.1")

    def test_permissions_profile_dont_mix_yml(self):
        """Dont mix perm set properties with profile"""
        with pytest.raises(ValidationError):
            PermissionsProfileFile.parse_from_yaml(
                StringIO(
                    (
                        """label: Profile
license: None
description: Life is full of surprises.
category_groups:
    - DataCategoryGroup1
activation_required: False
include:
    - Financial.schema"""
                    )
                )
            )

    def test_unsupported_option_yml(self):
        """Dont mix perm set properties with profile"""
        with pytest.raises(ValidationError):
            PermissionsProfileFile.parse_from_yaml(
                StringIO(
                    (
                        """label: Profile
licenses: None
description: Life is full of surprises.
include:
    - Financial.schema"""
                    )
                )
            )
