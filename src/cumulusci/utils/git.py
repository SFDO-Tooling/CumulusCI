import pathlib
from typing import Any, Optional, Tuple


def git_path(repo_root: str, tail: Any = None) -> Optional[pathlib.Path]:
    """Returns a Path to the .git directory in repo_root
    with tail appended (if present) or None if repo_root is not set.
    """
    path = None
    if repo_root:
        path = pathlib.Path(repo_root) / ".git"
        if tail is not None:
            path = path / str(tail)
    return path


def current_branch(repo_root: str) -> Optional[str]:
    branch_ref = git_path(repo_root, "HEAD").read_text().strip()
    if branch_ref.startswith("ref: "):
        return "/".join(branch_ref[5:].split("/")[2:])


def is_release_branch(branch_name: str, prefix: str) -> bool:
    """A release branch begins with the given prefix"""
    if not branch_name.startswith(prefix):
        return False
    parts = branch_name[len(prefix) :].split("__")
    return len(parts) == 1 and parts[0].isdigit()


def is_release_branch_or_child(branch_name: str, prefix: str) -> bool:
    if not branch_name.startswith(prefix):
        return False
    parts = branch_name[len(prefix) :].split("__")
    return len(parts) >= 1 and parts[0].isdigit()


def get_feature_branch_name(branch_name: str, prefix: str) -> Optional[str]:
    if branch_name.startswith(prefix):
        return branch_name[len(prefix) :]


def get_release_identifier(branch_name: str, prefix: str) -> Optional[str]:
    if is_release_branch_or_child(branch_name, prefix):
        return get_feature_branch_name(branch_name, prefix).split("__")[0]


def construct_release_branch_name(prefix: str, release_identifier: str) -> str:
    return f"{prefix}{release_identifier}"


def split_repo_url(url: str) -> Tuple[str, str]:
    url_parts = url.rstrip("/").split("/")

    name = url_parts[-1]
    if name.endswith(".git"):
        name = name[:-4]

    owner = url_parts[-2]
    # if it's an ssh url we might need to get rid of git@github.com
    owner = owner.split(":")[-1]

    return (owner, name)
