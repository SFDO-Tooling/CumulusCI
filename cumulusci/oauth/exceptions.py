from cumulusci.core.exceptions import CumulusCIException


class OAuth2Error(CumulusCIException):
    def __init__(self, *args, response=None):
        super().__init__(*args)
        # The HTTP response from the OAuth server, if there was one
        self.response = response


class SalesforceOAuth2Error(CumulusCIException):
    pass
