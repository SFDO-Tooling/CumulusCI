from cumulusci.core.exceptions import CumulusCIException


class OAuth2Error(CumulusCIException):
    pass


class SalesforceOAuth2Error(CumulusCIException):
    pass
