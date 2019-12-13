class CumulusCIException(Exception):
    """ Base class for all CumulusCI Exceptions """

    pass


class CumulusCIUsageError(CumulusCIException):
    """ An exception thrown due to improper usage which should be resolvable by proper usage """

    pass


class CumulusCIFailure(CumulusCIException):
    """ An exception representing a failure such as a Metadata deployment failure or a test failure.  CI systems can handle these to determine fail vs error status """

    pass


class NotInProject(CumulusCIUsageError):
    """ Raised when no project can be found in the current context """

    pass


class ProjectConfigNotFound(CumulusCIUsageError):
    """ Raised when a project is found in the current context but no configuration was found for the project """

    pass


class ProjectMinimumVersionError(CumulusCIException):
    pass


class KeychainNotFound(CumulusCIException):
    """ Raised when no keychain could be found """

    pass


class KeychainKeyNotFound(CumulusCIUsageError):
    """ Raised when the keychain key couldn't be found """

    pass


class OrgNotFound(CumulusCIUsageError):
    """ Raised when no org could be found by a given name in the project keychain """

    pass


class ServiceNotConfigured(CumulusCIUsageError):
    """ Raised when no service configuration could be found by a given name in the project keychain """

    pass


class ServiceNotValid(CumulusCIUsageError):
    """ Raised when no service configuration could be found by a given name in the project configuration """

    pass


class DependencyResolutionError(CumulusCIException):
    """ Raised when an issue is encountered while resolving a static dependency map """

    pass


class ConfigError(CumulusCIException):
    """ Raised when a configuration enounters an error """

    def __init__(self, message=None, config_name=None):
        super(ConfigError, self).__init__(message)
        self.message = message
        self.config_name = config_name

    def __str__(self):
        return f"{self.message} for config {self.config_name}"


class ConfigMergeError(ConfigError):
    """ Raised when merging configuration fails. """

    pass


class AntTargetException(CumulusCIException):
    """ Raised when a generic Ant target error occurs """

    pass


class DeploymentException(CumulusCIFailure):
    """ Raised when a metadata api deployment error occurs """

    pass


class ApexTestException(CumulusCIFailure):
    """ Raised when a build fails because of an Apex test failure """

    pass


class SalesforceCredentialsException(CumulusCIException):
    """ Raise when Salesforce credentials are invalid """

    pass


class TaskRequiresSalesforceOrg(CumulusCIUsageError):
    """ Raise when a task that requires a Salesforce org_config is not initialized with an org_config """

    pass


class TaskOptionsError(CumulusCIUsageError):
    """ Raise when a task's options are invalid """

    pass


class NamespaceNotFoundError(CumulusCIUsageError):
    """Raise when namespace is not found in project includes"""


class TaskNotFoundError(CumulusCIUsageError):
    """ Raise when task is not found in project config """

    pass


class FlowInfiniteLoopError(CumulusCIUsageError):
    """ Raised when a flow configuration creates a infinite loop """

    pass


class FlowConfigError(CumulusCIException):
    """ Raised when a flow configuration encounters an error """

    pass


class FlowNotFoundError(CumulusCIUsageError):
    """ Raise when flow is not found in project config """

    pass


class FlowNotReadyError(CumulusCIException):
    """ Raise when flow is called before it has been prepared """

    pass


class ScratchOrgException(CumulusCIException):
    """ Raise for errors related to scratch orgs """

    pass


class GithubException(CumulusCIException):
    """ Raise for errors related to GitHub """

    pass


class GithubApiError(CumulusCIException):
    pass


class GithubApiNotFoundError(CumulusCIException):
    pass


class GithubApiNoResultsError(CumulusCIException):
    pass


class GithubApiUnauthorized(CumulusCIException):
    pass


class SalesforceException(CumulusCIException):
    """ Raise for errors related to Salesforce """

    pass


class SalesforceDXException(CumulusCIException):
    """ Raise for errors related to Salesforce DX """

    pass


class SOQLQueryException(CumulusCIFailure):
    """ Raise for errors related to Salesforce DX """

    pass


class CommandException(CumulusCIFailure):
    """ Raise for errors coming from spawned CLI subprocesses """

    pass


class BrowserTestFailure(CumulusCIFailure):
    """ Raise when browser tests fail """

    pass


class ApexCompilationException(CumulusCIFailure):
    """ Raise when apex compilation fails """

    def __str__(self):
        line, problem = self.args
        return f"Apex compilation failed on line {line}: {problem}"


class ApexException(CumulusCIFailure):
    """ Raise when an Apex Exception is raised in an org """

    def __str__(self):
        message, stacktrace = self.args
        stacktrace = "\n  ".join(stacktrace.splitlines())
        return f"Apex error: {message}\n  Stacktrace:\n  {stacktrace}"


class PushApiObjectNotFound(CumulusCIException):
    """ Raise when Salesforce Push API object is not found """

    pass


class RobotTestFailure(CumulusCIFailure):
    """ Raise when a robot test fails in a test suite """

    pass


class BulkDataException(CumulusCIFailure):
    """ Raise for errors from bulkdata tasks """

    pass
