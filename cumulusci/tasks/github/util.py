from builtins import str
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

        # prepare dir args
        local_dir, repo_dir = self._validate_dirs(local_dir, repo_dir)

        # get ref to branch HEAD
        head = self.repo.ref("heads/{}".format(branch))

        # get commit pointed to by HEAD
        commit = self.repo.git_commit(head.object.sha)

        # get tree of commit
        tree = self.repo.tree(commit.tree.sha)  # shallow tree
        tree = tree.recurse()  # recurse/flatten
        tree = tree.to_json()  # convert to native types

        # create new tree (delete, update)
        new_tree_list = []
        for item in tree["tree"]:
            if item["type"] == "tree":
                # remove sub-trees as they are implied by blob paths
                self.logger.debug("Removing tree: {}".format(item["path"]))
                continue
            if not item["path"].startswith(repo_dir):
                # outside target dir in repo - keep in tree
                self.logger.debug(
                    "Unchanged (outside target path): {}".format(item["path"])
                )
                new_tree_list.append(item)
                continue
            len_path = (len(repo_dir) + 1) if repo_dir else 0
            item_subpath = item["path"][len_path:]
            local_file = os.path.join(local_dir, item_subpath)
            if not os.path.isfile(local_file):
                # delete blob from tree
                self.logger.debug("Delete: {}".format(item["path"]))
                continue
            with io.open(local_file, "rb") as f:
                content = f.read()
            header = b"blob " + str(len(content)).encode() + b"\0"
            sha = hashlib.sha1(header + content).hexdigest()
            new_item = item.copy()
            if sha != item["sha"]:
                self.logger.debug("Update: {}".format(local_file))
                if dry_run:
                    self.logger.info(
                        "[dry_run] Skipping creation of blob "
                        + "for file: {}".format(local_file)
                    )
                    blob_sha = None
                else:
                    self.logger.info(
                        "Creating blob for updated file: {}".format(local_file)
                    )
                    blob_sha = self._create_blob(content)
                    self.logger.debug("Blob created: {}".format(blob_sha))
                new_item["sha"] = blob_sha
            else:
                self.logger.debug("Unchanged: {}".format(item["path"]))
            new_tree_list.append(new_item)

        # add new files to tree
        new_tree_target_subpaths = []
        for item in new_tree_list:
            if not item["path"].startswith(repo_dir):
                # skip items not in target dir
                continue
            len_path = (len(repo_dir) + 1) if repo_dir else 0
            new_tree_target_subpaths.append(item["path"][len_path:])
        for root, dirs, files in os.walk(local_dir):
            for filename in files:
                if filename.startswith("."):
                    # skip hidden files
                    continue
                local_file = os.path.join(root, filename)
                local_file_subpath = local_file[(len(local_dir) + 1) :]
                if local_file_subpath not in new_tree_target_subpaths:
                    with io.open(local_file, "rb") as f:
                        content = f.read()
                    if dry_run:
                        self.logger.info(
                            "[dry_run] Skipping creation of "
                            + "blob for new file: {}".format(local_file)
                        )
                        blob_sha = None
                    else:
                        self.logger.info(
                            "Creating blob for new file: {}".format(local_file)
                        )
                        blob_sha = self._create_blob(content)
                        self.logger.debug("Blob created: {}".format(blob_sha))
                    repo_path = (repo_dir + "/") if repo_dir else ""
                    new_item = {
                        "path": "{}{}".format(repo_path, local_file_subpath),
                        "mode": "100644",
                        "type": "blob",
                        "sha": blob_sha,
                    }
                    new_tree_list.append(new_item)

        # generate summary of changes
        self.logger.info("Summary of changes:")
        new_shas = [item["sha"] for item in new_tree_list]
        new_paths = [item["path"] for item in new_tree_list]
        old_paths = [item["path"] for item in tree["tree"]]
        old_tree_list = []
        for item in tree["tree"]:
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
        if new_tree_list == old_tree_list:
            self.logger.warning("No changes found, aborting commit")
            return

        # create new tree
        if dry_run:
            self.logger.info("[dry_run] Skipping creation of new tree")
        else:
            self.logger.info("Creating new tree")
            new_tree = self.repo.create_tree(new_tree_list, None)
            if not new_tree:
                raise GithubException("Failed to create tree")

        # create new commit
        if commit_message is None:
            commit_message = "Commit dir {} to {}/{}/{} via CumulusCI".format(
                local_dir, self.repo.owner, self.repo.name, repo_dir
            )
        if dry_run:
            self.logger.info("[dry_run] Skipping creation of new commit")
        else:
            self.logger.info("Creating new commit")
            new_commit = self.repo.create_commit(
                message=commit_message,
                tree=new_tree.sha,
                parents=[commit.sha],
                author=self.author,
                committer=self.author,
            )
            if not new_commit:
                raise GithubException("Failed to create commit")

        # update HEAD
        if dry_run:
            self.logger.info("[dry_run] Skipping call to update HEAD")
        else:
            self.logger.info("Updating HEAD")
            success = head.update(new_commit.sha)
            if not success:
                raise GithubException("Failed to update HEAD")

    def _create_blob(self, content):
        try:
            content = content.decode("utf-8")
            blob_sha = self.repo.create_blob(content, "utf-8")
        except UnicodeDecodeError:
            content = base64.b64encode(content)
            blob_sha = self.repo.create_blob(content, "base64")
        if not blob_sha:
            raise GithubException("Failed to create blob")
        return blob_sha
