import base64
import hashlib
import logging
import os
from pathlib import Path
from typing import Optional, Tuple

from github3.git import Commit, Tree

from cumulusci.core.exceptions import GithubException


class CommitDir(object):
    """Commit all changes in local_dir to branch/repo_dir"""

    def __init__(self, repo, logger=None, author=None):
        """
        repo: github3.py Repository object, authenticated
        logger (optional): python logger object
        author (optional): dict of name, email, time - default uses auth'd info
        """
        self.repo = repo
        if not logger:
            logger = logging.getLogger(os.path.basename(__file__))
        self.logger = logger
        self.author = author or {}

    def _validate_dirs(self, local_dir, repo_dir):
        local_dir = os.path.abspath(local_dir)
        if not os.path.isdir(local_dir):
            raise GithubException(f"Not a dir: {local_dir}")
        # do not use os.path because repo_dir is not local
        if repo_dir is None:
            repo_dir = ""
        if repo_dir.startswith("."):
            repo_dir = repo_dir[1:]
        if repo_dir.startswith("/"):
            repo_dir = repo_dir[1:]
        if repo_dir.endswith("/"):
            repo_dir = repo_dir[:-1]
        return local_dir, repo_dir

    def __call__(
        self, local_dir, branch, repo_dir=None, commit_message=None, dry_run=False
    ):
        """
        local_dir: path to local directory to commit
        branch: target branch name
        repo_dir: target path within repo - use '' for repo root
        commit_message: message for git commit
        dry_run: skip creating GitHub data if True
        """

        self.dry_run = dry_run
        # prepare dir args
        self.local_dir, self.repo_dir = self._validate_dirs(local_dir, repo_dir)
        self._set_git_data(branch)

        self.new_tree_list = [self._create_new_tree_item(item) for item in self.tree]
        self.new_tree_list = [item for item in self.new_tree_list if item]
        self._add_new_files_to_tree(self.new_tree_list)

        if not self.new_tree_list:
            self.logger.warning("No changes found, aborting commit")
            return self.parent_commit

        self._summarize_changes(self.tree, self.new_tree_list)
        new_tree = self._create_tree(self.new_tree_list)
        new_commit = self._create_commit(commit_message, new_tree)
        self._update_head(new_commit)
        return new_commit

    def _set_git_data(self, branch):
        # get ref to branch HEAD
        self.head = self.repo.ref(f"heads/{branch}")

        # get commit pointed to by HEAD
        self.parent_commit: Commit = self.repo.git_commit(self.head.object.sha)

        # get tree of commit as dict
        orig_tree: Tree = self.repo.tree(self.parent_commit.tree.sha, recursive=True)
        self.tree = [
            git_hash.as_dict() for git_hash in orig_tree.tree if git_hash.type != "tree"
        ]

    def _create_new_tree_item(self, item: dict) -> Optional[dict]:
        """Given an Git tree element, returns None if it is unchanged, or
        a new element if it has been deleted or updated.
        """
        if not item["path"].startswith(self.repo_dir):
            # outside target dir in repo - keep in tree
            self.logger.debug(f'Unchanged (outside target path): {item["path"]}')
            return None

        local_path, content = self._find_and_read_item(item)
        new_item = item.copy()
        if content is None:
            # delete blob from tree by setting 'sha' to null
            self.logger.debug(f"Delete: {item['path']}")
            new_item["sha"] = None
        elif self._item_changed(item, content):
            # we need to delete the sha key because GH returns an error if
            # both 'sha' and 'contents' are passed.
            self.logger.debug(f"Update: {local_path}")
            new_item.pop("sha", None)
            new_item.update(self._get_content_or_sha(content, self.dry_run))
        else:
            self.logger.debug(f'Unchanged: {item["path"]}')
            return None
        return new_item

    def _add_new_files_to_tree(self, new_tree_list):
        new_tree_target_subpaths = [
            self._get_item_sub_path(item)
            for item in self.tree
            if item["path"].startswith(self.repo_dir)
        ]

        for root, _, files in os.walk(self.local_dir):
            for filename in files:
                if not filename.startswith("."):
                    local_file = os.path.join(root, filename)
                    local_file_subpath = local_file[(len(self.local_dir) + 1) :]
                    if local_file_subpath not in new_tree_target_subpaths:
                        repo_path = f"{self.repo_dir}/" if self.repo_dir else ""
                        new_item = {
                            "path": f'{repo_path}{local_file_subpath.replace(os.sep, "/")}',
                            "mode": "100644",  # FIXME: This is wrong
                            "type": "blob",
                        }
                        new_item.update(
                            self._get_content_or_sha(
                                Path(local_file).read_bytes(), self.dry_run
                            )
                        )
                        new_tree_list.append(new_item)

    def _summarize_changes(self, old_tree_list, new_tree_list):
        self.logger.info("Summary of changes:")
        old_paths = [item["path"] for item in old_tree_list]

        def join_paths(paths):
            return "\n".join(f"\t{path}" for path in paths)

        deleted_paths = join_paths(
            [item["path"] for item in new_tree_list if item.get("sha", "") is None]
        )
        if deleted_paths:
            self.logger.warning(f"Deleted:\n{deleted_paths}")

        new_paths = join_paths(
            [
                item["path"]
                for item in new_tree_list
                if "content" in item and item["path"] not in old_paths
            ]
        )
        if new_paths:
            self.logger.info(f"Added:\n{new_paths}")

        updated_paths = join_paths(
            [
                item["path"]
                for item in new_tree_list
                if "content" in item and item["path"] in old_paths
            ]
        )
        if updated_paths:
            self.logger.info(f"Updated:\n{updated_paths}")

    def _create_tree(self, new_tree_list):
        new_tree = None
        if self.dry_run:
            self.logger.info("[dry_run] Skipping creation of new tree")
        else:
            self.logger.info("Creating new tree")
            new_tree = self.repo.create_tree(
                new_tree_list, base_tree=self.parent_commit.tree.sha
            )
            if not new_tree:
                raise GithubException("Failed to create tree")
        return new_tree

    def _create_commit(self, commit_message, new_tree):
        if commit_message is None:
            commit_message = f"Commit dir {self.local_dir} to {self.repo.owner}/{self.repo.name}/{self.repo_dir} via CumulusCI"

        new_commit = None
        if self.dry_run:
            self.logger.info("[dry_run] Skipping creation of new commit")
        else:
            self.logger.info("Creating new commit")
            commit_info = {
                "message": commit_message,
                "tree": new_tree.sha,
                "parents": [self.parent_commit.sha],
            }
            if self.author:
                commit_info["author"] = self.author
                commit_info["committer"] = self.author
            new_commit = self.repo.create_commit(**commit_info)
            if not new_commit:
                raise GithubException("Failed to create commit")
        return new_commit

    def _update_head(self, new_commit):
        if self.dry_run:
            self.logger.info("[dry_run] Skipping call to update HEAD")
        else:
            self.logger.info("Updating HEAD")
            success = self.head.update(new_commit.sha)
            if not success:
                raise GithubException("Failed to update HEAD")

    def _get_item_sub_path(self, item):
        len_path = (len(self.repo_dir) + 1) if self.repo_dir else 0
        return item["path"][len_path:]

    def _find_and_read_item(self, item) -> Tuple[Path, Optional[bytes]]:
        item_subpath = self._get_item_sub_path(item)
        pth = Path(self.local_dir, item_subpath)
        contents = pth.read_bytes() if pth.exists() else None
        return pth, contents

    def _item_changed(self, item: dict, content: bytes) -> bool:
        header = b"blob " + str(len(content)).encode() + b"\0"
        return hashlib.sha1(header + content).hexdigest() != item["sha"]

    def _get_content_or_sha(self, content, dry_run) -> dict:
        """Given file contents as bytes, returns a dict with file contents.

        If the contents are text: {'contents': contents as str}
        If the contents are binary: {'sha': hash of the uploaded blob}
        """
        if dry_run:
            self.logger.info("[dry_run] Skipping creation of blob for new file")
            return {"content": None}
        try:
            content = content.decode("utf-8")
            return {"content": content}
        except UnicodeDecodeError:
            return self._create_blob(content)

    def _create_blob(self, contents: bytes) -> dict:
        self.logger.info("Creating blob for binary file")
        content: bytes = base64.b64encode(contents)
        blob_sha: str = self.repo.create_blob(content.decode("utf-8"), "base64")
        if not blob_sha:
            raise GithubException("Failed to create blob")
        self.logger.debug(f"Blob created: {blob_sha}")
        return {"sha": blob_sha}
