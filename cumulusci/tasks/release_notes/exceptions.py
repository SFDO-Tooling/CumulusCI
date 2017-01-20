from cumulusci.core.exceptions import CumulusCIException


class GithubApiNotFoundError(CumulusCIException):
    pass


class GithubApiNoResultsError(CumulusCIException):
    pass


class GithubApiUnauthorized(CumulusCIException):
    pass


class LastReleaseTagNotFoundError(CumulusCIException):
    pass
