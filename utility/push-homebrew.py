#!/usr/bin/env python3

import os
import sys

from github3 import login

from cumulusci import __version__ as version
from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.utils import import_class

FORMULA_FILE = sys.argv[1]
TARGET_FILE = "cumulusci.rb"
GITHUB_ORG = "SFDO-Tooling"
GITHUB_REPO = "homebrew-sfdo"
BRANCH_NAME = "cci-" + version


def get_github_user():
    proj = BaseGlobalConfig().get_project_config()
    keychain_key = os.environ.get("CUMULUSCI_KEY")
    keychain_class = os.environ.get(
        "CUMULUSCI_KEYCHAIN_CLASS", proj.cumulusci__keychain
    )
    keychain_class = import_class(keychain_class)
    keychain = keychain_class(proj, keychain_key)
    github_config = keychain.get_service("github")
    return github_config.username, github_config.password


def get_repo():
    username, password = get_github_user()
    gh = login(username=username, password=password)
    return gh.repository(GITHUB_ORG, GITHUB_REPO)


def create_branch(repo):
    head_sha = repo.ref("heads/master").object.sha
    branch_ref = f"refs/heads/{BRANCH_NAME}"
    print(f"Creating new branch from {head_sha[:8]} at {branch_ref}")
    new_branch = repo.create_ref(branch_ref, head_sha)


def read_formula():
    with open(FORMULA_FILE, "r") as f:
        content = f.read().encode("utf-8")
    return content


def create_pull_request(repo):
    msg = f"Bump cumulusci to version {version}"
    new_commit = repo.file_contents(f"/{TARGET_FILE}").update(
        msg, read_formula(), branch=BRANCH_NAME
    )
    print(f"Updated {TARGET_FILE} to {new_commit['commit'].sha[:8]}")
    pull_request = repo.create_pull(msg, "master", BRANCH_NAME)
    print(f"Created pull request at {pull_request.url}")


def main():
    repo = get_repo()
    create_branch(repo)
    create_pull_request(repo)


if __name__ == "__main__":
    main()
