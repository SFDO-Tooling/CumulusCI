
class NotInProject(Exception):
    """ Raised when no project can be found in the current context """
    pass

class ProjectConfigNotFound(Exception):
    """ Raised when a project is found in the current context but no configuration was found for the project """
    pass
