# run this in a separate process to not confuse
# the module table
import os
from unittest.mock import patch

import pytest

from cumulusci.utils.deprecation import ClassMovedWarning


class TestConfigBackwardsCompatibility:
    @patch.dict(os.environ)
    def test_temporary_backwards_compatibility_hacks(self):
        with pytest.warns(ClassMovedWarning):

            from cumulusci.core.config.OrgConfig import OrgConfig

            assert isinstance(OrgConfig, type)

        with pytest.warns(ClassMovedWarning):
            from cumulusci.core.config.ScratchOrgConfig import ScratchOrgConfig  # noqa

            assert isinstance(ScratchOrgConfig, type)

        with pytest.warns(ClassMovedWarning):
            from cumulusci.core.config.BaseConfig import BaseConfig

            assert isinstance(BaseConfig, type)

        with pytest.warns(ClassMovedWarning):
            from cumulusci.core.config.BaseTaskFlowConfig import BaseTaskFlowConfig

            assert isinstance(BaseTaskFlowConfig, type)
