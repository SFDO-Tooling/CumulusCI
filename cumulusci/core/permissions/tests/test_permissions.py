import pytest
from cumulusci.core.permissions.permissions import PermissionsFile


class TestPermissionsUnitYml:
    def test_permissions_unit_yml(self):
        validated = PermissionsFile.parse_from_yaml(
            "cumulusci/core/permissions/tests/test_permissions_unit.yml"
        )
        # Testing a deeply nested value for verification
        assert validated.schema_.defaults["read_all"].object_permissions.create is True

    def test_permissions_unit_yml_error(self):
        with pytest.raises(ValueError):
            validated = PermissionsFile.parse_from_yaml(
                "cumulusci/core/permissions/tests/test_permissions_unit_bad.yml"
            )
            assert (
                validated.schema_.defaults["read_all"].object_permissions.create is True
            )
