import pathlib


def git_path(repo_root, tail=None):
    """Returns a Path to the .git directory in repo_root
    with tail appended (if present) or None if repo_root is not set.
    """
    path = None
    if repo_root and (pathlib.Path(repo_root) / ".git").exists():
        # When we're a source tarball, we'll have a repo_root but no .git/HEAD.
        path = pathlib.Path(repo_root) / ".git"
        if tail is not None:
            path = path / str(tail)
    return path


def current_branch(repo_root):
    path = git_path(repo_root, "HEAD")
    if path:
        branch_ref = path.read_text().strip()
        if branch_ref.startswith("ref: "):
            return "/".join(branch_ref[5:].split("/")[2:])
