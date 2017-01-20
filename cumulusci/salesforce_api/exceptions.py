from cumulusci.core.exceptions import CumulusCIException


class MetadataApiError(CumulusCIException):

    def __init__(self, message, response):
        super(MetadataApiError, self).__init__(message)
        self.response = response


class MissingOAuthError(CumulusCIException):
    pass


class MissingOrgCredentialsError(CumulusCIException):
    pass
