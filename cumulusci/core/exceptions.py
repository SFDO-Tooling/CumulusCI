from __future__ import unicode_literals
class CumulusCIException(Exception):
    pass


class NotInProject(CumulusCIException):
    """ Raised when no project can be found in the current context """
    pass


class ProjectConfigNotFound(CumulusCIException):
    """ Raised when a project is found in the current context but no configuration was found for the project """
    pass


class KeychainNotFound(CumulusCIException):
    """ Raised when no keychain could be found """
    pass


class KeychainKeyNotFound(CumulusCIException):
    """ Raised when the keychain key couldn't be found """


class OrgNotFound(CumulusCIException):
    """ Raised when no org could be found by a given name in the project keychain """
    pass


class ServiceNotConfigured(CumulusCIException):
    """ Raised when no service configuration could be found by a given name in the project keychain """
    pass


class ServiceNotValid(CumulusCIException):
    """ Raised when no service configuration could be found by a given name in the project configuration """
    pass

class DependencyResolutionError(CumulusCIException):
    """ Raised when an issue is encountered while resolving a static dependency map """
    pass

class ConfigError(CumulusCIException):
    """ Raised when a configuration enounters an error """
    pass


class AntTargetException(CumulusCIException):
    """ Raised when a generic Ant target error occurs """
    pass


class DeploymentException(CumulusCIException):
    """ Raised when a metadata api deployment error occurs """
    pass


class ApexTestException(CumulusCIException):
    """ Raised when a build fails because of an Apex test failure """
    pass


class SalesforceCredentialsException(CumulusCIException):
    """ Raise when Salesforce credentials are invalid """
    pass


class TaskRequiresSalesforceOrg(CumulusCIException):
    """ Raise when a task that requires a Salesforce org_config is not initialized with an org_config """
    pass


class TaskOptionsError(CumulusCIException):
    """ Raise when a task's options are invalid """
    pass


class GithubNotConfigured(CumulusCIException):
    """ Raise when attempting to get the Github configuration from the keychain and no configuration is set """
    pass


class MrbelvedereNotConfigured(CumulusCIException):
    """ Raise when attempting to get the mrbelvedere configuration from the keychain and no configuration is set """
    pass


class ApexTestsDBNotConfigured(CumulusCIException):
    """ Raise when attempting to get the ApexTestsDB configuration from the keychain and no configuration is set """
    pass


class TaskNotFoundError(CumulusCIException):
    """ Raise when task is not found in project config """
    pass

class FlowInfiniteLoopError(CumulusCIException):
    """ Raised when a flow configuration creates a infinite loop """
    pass

class FlowConfigError(CumulusCIException):
    """ Raised when a flow configuration encounters an error """
    pass

class FlowNotFoundError(CumulusCIException):
    """ Raise when flow is not found in project config """
    pass

class FlowNotReadyError(CumulusCIException):
    """ Raise when flow is called before it has been prepared """
    pass


class MrbelvedereError(CumulusCIException):
    """ Raise for errors from mrbelvedere installer """
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


class SOQLQueryException(CumulusCIException):
    """ Raise for errors related to Salesforce DX """
    pass


class CommandException(CumulusCIException):
    """ Raise for errors coming from spawned CLI subprocesses """
    pass


class BrowserTestFailure(CommandException):
    """ Raise when browser tests fail """
    pass


class ApexCompilationException(CumulusCIException):
    """ Raise when apex compilation fails """
    pass


class ApexException(CumulusCIException):
    """ Raise when an Apex Exception is raised in an org """
    pass


class PushApiObjectNotFound(CumulusCIException):
    """ Raise when Salesforce Push API object is not found """
    pass

class RobotTestFailure(CumulusCIException):
    """ Raise when a robot test fails in a test suite """
    pass
