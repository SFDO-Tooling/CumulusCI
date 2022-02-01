import pytest


class TestConfigBackwardsCompatibility:
    def test_temporary_backwards_compatiblity_hacks(self):
        with pytest.warns(UserWarning):
            from cumulusci.core.config.OrgConfig import OrgConfig

            assert isinstance(OrgConfig, type)

        with pytest.warns(UserWarning):
            from cumulusci.core.config.ScratchOrgConfig import ScratchOrgConfig  # noqa

            assert isinstance(ScratchOrgConfig, type)

        with pytest.warns(UserWarning):
            from cumulusci.core.config.BaseConfig import BaseConfig

            assert isinstance(BaseConfig, type)

        with pytest.warns(UserWarning):
            from cumulusci.core.config.BaseTaskFlowConfig import BaseTaskFlowConfig

            assert isinstance(BaseTaskFlowConfig, type)
