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
