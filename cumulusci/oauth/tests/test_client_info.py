from cumulusci.oauth.client_info import OAuthClientInfo


class TestOAuthClientInfo:
    def test_obj_creation(self):
        client_info = OAuthClientInfo(
            client_id="asdf",
            auth_uri="http://localhost/authorize",
            token_uri="http://localhost/token",
        )
        assert client_info.callback_url == "http://localhost:8080/callback"
