from cumulusci.core.exceptions import CumulusCIException


class OAuthError(CumulusCIException):
    pass


class SalesforceOAuthError(CumulusCIException):
    pass
