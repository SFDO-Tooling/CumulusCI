import pathlib


def git_path(repo_root, tail=None):
    """Returns a Path to the .git directory in repo_root
    with tail appended (if present) or None if repo_root is not set.
    """
    path = None
    if repo_root:
        path = pathlib.Path(repo_root) / ".git"
        if tail is not None:
            path = path / str(tail)
    return path


def current_branch(repo_root):
    branch_ref = git_path(repo_root, "HEAD").read_text().strip()
    if branch_ref.startswith("ref: "):
        return "/".join(branch_ref[5:].split("/")[2:])


def is_release_branch(branch_name, prefix):
    """A release branch begins with the given prefix"""
    if not branch_name.startswith(prefix):
        return False
    parts = branch_name[len(prefix) :].split("__")
    return len(parts) == 1 and parts[0].isdigit()


def is_release_branch_or_child(branch_name, prefix):
    if not branch_name.startswith(prefix):
        return False
    parts = branch_name[len(prefix) :].split("__")
    return len(parts) >= 1 and parts[0].isdigit()


def get_release_identifier(branch_name, prefix):
    if is_release_branch_or_child(branch_name, prefix):
        return branch_name[len(prefix) :].split("__")[0]


def construct_release_branch(prefix, release_identifier):
    return f"{prefix}{release_identifier}"