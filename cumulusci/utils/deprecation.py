from warnings import warn


class ClassMovedWarning(FutureWarning):
    pass


def warn_moved(new, old):
    msg = f"Deprecation warning: Please import from {new} rather than {old}"

    warn(msg, ClassMovedWarning)
