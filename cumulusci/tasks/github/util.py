import base64
import hashlib
import io
import logging
import os

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
        self.author = author if author else {}

    def _validate_dirs(self, local_dir, repo_dir):
        local_dir = os.path.abspath(local_dir)
        if not os.path.isdir(local_dir):
            raise GithubException("Not a dir: {}".format(local_dir))
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

        tree_unchanged = self._summarize_changes(self.new_tree_list)
        if tree_unchanged:
            self.logger.warning("No changes found, aborting commit")
            return self.parent_commit

        new_tree = self._create_tree(self.new_tree_list)
        new_commit = self._create_commit(commit_message, new_tree)
        self._update_head(new_commit)
        return new_commit

    def _set_git_data(self, branch):
        # get ref to branch HEAD
        self.head = self.repo.ref("heads/{}".format(branch))

        # get commit pointed to by HEAD
        self.parent_commit = self.repo.git_commit(self.head.object.sha)

        # get tree of commit as dict
        self.tree = self.repo.tree(self.parent_commit.tree.sha, recursive=True)
        self.tree = [
            self._git_hash_to_dict(git_hash)
            for git_hash in self.tree.tree
            if git_hash.type != "tree"
        ]

    def _git_hash_to_dict(self, git_hash):
        return {
            "sha": git_hash.sha,
            "mode": git_hash.mode,
            "path": git_hash.path,
            "size": git_hash.size,
            "type": git_hash.type,
        }

    def _create_new_tree_item(self, item):
        if not item["path"].startswith(self.repo_dir):
            # outside target dir in repo - keep in tree
            self.logger.debug(
                "Unchanged (outside target path): {}".format(item["path"])
            )
            return item

        local_file, content = self._read_item_content(item)
        new_item = item.copy()
        if content is None:
            # delete blob from tree
            self.logger.debug(f"Delete: {item['path']}")
            return content
        elif self._item_changed(item, content):
            self.logger.debug("Update: {}".format(local_file))
            blob_sha = self._create_blob(content, local_file)
            new_item["sha"] = blob_sha
        else:
            self.logger.debug("Unchanged: {}".format(item["path"]))
        return new_item

    def _add_new_files_to_tree(self, new_tree_list):
        new_tree_target_subpaths = [
            self._get_item_sub_path(item)
            for item in new_tree_list
            if item["path"].startswith(self.repo_dir)
        ]

        for root, dirs, files in os.walk(self.local_dir):
            for filename in files:
                if not filename.startswith("."):
                    local_file = os.path.join(root, filename)
                    local_file_subpath = local_file[(len(self.local_dir) + 1) :]
                    if local_file_subpath not in new_tree_target_subpaths:
                        with io.open(local_file, "rb") as f:
                            content = f.read()
                        repo_path = (self.repo_dir + "/") if self.repo_dir else ""
                        new_item = {
                            "path": "{}{}".format(
                                repo_path, local_file_subpath.replace(os.sep, "/")
                            ),
                            "mode": "100644",
                            "type": "blob",
                            "sha": self._create_blob(content, local_file),
                        }
                        new_tree_list.append(new_item)

    def _summarize_changes(self, new_tree_list):
        self.logger.info("Summary of changes:")
        new_shas = [item["sha"] for item in new_tree_list]
        new_paths = [item["path"] for item in new_tree_list]
        old_paths = [item["path"] for item in self.tree]
        old_tree_list = []
        for item in self.tree:
            if item["type"] == "tree":
                continue
            old_tree_list.append(item)
            if item["path"] not in new_paths:
                self.logger.warning("Delete:\t{}".format(item["path"]))
            elif item["sha"] not in new_shas:
                self.logger.info("Update:\t{}".format(item["path"]))
        for item in new_tree_list:
            if item["path"] not in old_paths:
                self.logger.info("Add:\t{}".format(item["path"]))
        return new_tree_list == old_tree_list

    def _create_tree(self, new_tree_list):
        new_tree = None
        if self.dry_run:
            self.logger.info("[dry_run] Skipping creation of new tree")
        else:
            self.logger.info("Creating new tree")
            new_tree = self.repo.create_tree(new_tree_list, None)
            if not new_tree:
                raise GithubException("Failed to create tree")
        return new_tree

    def _create_commit(self, commit_message, new_tree):
        if commit_message is None:
            commit_message = "Commit dir {} to {}/{}/{} via CumulusCI".format(
                self.local_dir, self.repo.owner, self.repo.name, self.repo_dir
            )
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

    def _read_item_content(self, item):
        item_subpath = self._get_item_sub_path(item)
        local_file = os.path.join(self.local_dir, item_subpath)
        if not os.path.isfile(local_file):
            return local_file, None
        with io.open(local_file, "rb") as f:
            content = f.read()
        return local_file, content

    def _item_changed(self, item, content):
        header = b"blob " + str(len(content)).encode() + b"\0"
        return hashlib.sha1(header + content).hexdigest() != item["sha"]

    def _create_blob(self, content, local_file):
        if self.dry_run:
            self.logger.info(
                "[dry_run] Skipping creation of "
                + "blob for new file: {}".format(local_file)
            )
            blob_sha = None
        else:
            self.logger.info("Creating blob for new file: {}".format(local_file))
            try:
                content = content.decode("utf-8")
                blob_sha = self.repo.create_blob(content, "utf-8")
            except UnicodeDecodeError:
                content = base64.b64encode(content)
                blob_sha = self.repo.create_blob(content.decode("utf-8"), "base64")
            if not blob_sha:
                raise GithubException("Failed to create blob")
        self.logger.debug("Blob created: {}".format(blob_sha))
        return blob_sha
