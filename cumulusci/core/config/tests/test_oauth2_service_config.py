import pytest

from cumulusci.core.config.oauth2_service_config import OAuth2ServiceConfig


class TestOAuth2ServiceConfig:
    def test_connect_method_not_implemented(self):
        class TestConfig(OAuth2ServiceConfig):
            def __init__(self):
                super().__init__()

        t = TestConfig()
        with pytest.raises(NotImplemented):
            t.connect()
