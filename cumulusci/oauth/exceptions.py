from cumulusci.core.exceptions import CumulusCIException


class SalesforceOAuthError(CumulusCIException):
    pass


class RequestOauthTokenError(CumulusCIException):

    def __init__(self, message, response):
        super(RequestOauthTokenError, self).__init__(message)
        self.response = response
