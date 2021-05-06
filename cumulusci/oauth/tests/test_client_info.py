from cumulusci.oauth.client_info import OAuth2ClientInfo


class TestOAuth2ClientInfo:
    def test_obj_creation(self):
        client_info = OAuth2ClientInfo(
            client_id="asdf",
            auth_uri="http://localhost/authorize",
            token_uri="http://localhost/token",
        )
        assert client_info.callback_url == "http://localhost:8080/callback"
