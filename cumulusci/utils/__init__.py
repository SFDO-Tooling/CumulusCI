import contextlib
import fnmatch
import io
import math
import os
import re
import shutil
import sys
import tempfile
import textwrap
import zipfile
from datetime import datetime

import requests
import sarge
from .xml import (
    elementtree_parse_file,
    removeXmlElement,
    remove_xml_element_file,
    remove_xml_element_string,
    remove_xml_element,
)

__IMPORTED_ONLY_FOR_BACKWARDS_COMPATIBILITY = (
    elementtree_parse_file,
    removeXmlElement,
    remove_xml_element_file,
    remove_xml_element_string,
    remove_xml_element,
)

CUMULUSCI_PATH = os.path.realpath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "../..")
)
META_XML_CLEAN_DIRS = ("classes/", "triggers/", "pages/", "aura/", "components/")
API_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
DATETIME_LEN = len("2018-08-07T16:00:56.000")

BREW_UPDATE_CMD = "brew upgrade cumulusci"
PIP_UPDATE_CMD = "pip install --upgrade cumulusci"
PIPX_UPDATE_CMD = "pipx upgrade cumulusci"


def parse_api_datetime(value):
    """ parse a datetime returned from the salesforce API.

    in python 3 we should just use a strptime %z, but until then we're just going
    to assert that its a fixed offset of +0000 since thats the observed behavior. getting
    python 2 to support fixed offset parsing is too complicated for what we need imo."""
    dt = datetime.strptime(value[0:DATETIME_LEN], API_DATE_FORMAT)
    offset_str = value[DATETIME_LEN:]
    assert offset_str in ["+0000", "Z"], "The Salesforce API returned a weird timezone."
    return dt


def findReplace(find, replace, directory, filePattern, logger=None, max=None):
    for path, dirs, files in os.walk(os.path.abspath(directory)):
        for filename in fnmatch.filter(files, filePattern):
            filepath = os.path.join(path, filename)
            with io.open(filepath, encoding="utf-8") as f:
                s = f.read()
            if max:
                s_updated = s.replace(find, replace, max)
            else:
                s_updated = s.replace(find, replace)
            if s != s_updated:
                if logger:
                    logger.info("Updating {}".format(filepath))
                with io.open(filepath, "w", encoding="utf-8") as f:
                    f.write(s_updated)


def findReplaceRegex(find, replace, directory, filePattern, logger=None):
    pattern = re.compile(find)
    for path, dirs, files in os.walk(os.path.abspath(directory)):
        for filename in fnmatch.filter(files, filePattern):
            filepath = os.path.join(path, filename)
            with io.open(filepath, encoding="utf-8") as f:
                s = f.read()
            s_updated = pattern.sub(replace, s)
            if s != s_updated:
                if logger:
                    logger.info("Updating {}".format(filepath))
                with io.open(filepath, "w", encoding="utf-8") as f:
                    f.write(s_updated)


def findRename(find, replace, directory, logger=None):
    for path, dirs, files in os.walk(os.path.abspath(directory)):
        for filename in files:
            filepath = os.path.join(path, filename)
            if logger:
                logger.info("Renaming {}".format(filepath))
            os.rename(filepath, os.path.join(path, filename.replace(find, replace)))


def download_extract_zip(url, target=None, subfolder=None, headers=None):
    if not headers:
        headers = {}
    resp = requests.get(url, headers=headers)
    zip_content = io.BytesIO(resp.content)
    zip_file = zipfile.ZipFile(zip_content)
    if subfolder:
        zip_file = zip_subfolder(zip_file, subfolder)
    if target:
        zip_file.extractall(target)
        return
    return zip_file


def download_extract_github(
    github_api, repo_owner, repo_name, subfolder=None, ref=None
):
    return download_extract_github_from_repo(
        github_api.repository(repo_owner, repo_name), subfolder, ref
    )


def download_extract_github_from_repo(github_repo, subfolder=None, ref=None):
    if not ref:
        ref = github_repo.default_branch
    zip_content = io.BytesIO()
    github_repo.archive("zipball", zip_content, ref=ref)
    zip_file = zipfile.ZipFile(zip_content)
    path = sorted(zip_file.namelist())[0]
    if subfolder:
        path = path + subfolder
    zip_file = zip_subfolder(zip_file, path)
    return zip_file


def zip_subfolder(zip_src, path):
    if not path.endswith("/"):
        path = path + "/"

    zip_dest = zipfile.ZipFile(io.BytesIO(), "w", zipfile.ZIP_DEFLATED)
    for name in zip_src.namelist():
        if not name.startswith(path):
            continue

        content = zip_src.read(name)
        rel_name = name.replace(path, "", 1)

        if rel_name:
            zip_dest.writestr(rel_name, content)

    return zip_dest


def process_text_in_directory(path, process_file):
    """Process each file in a directory using the `process_file` function.

    `process_file` should be a function which accepts a filename and content as text
    and returns a (possibly modified) filename and content.  The file will be
    updated with the new content, and renamed if necessary.

    Files with content that cannot be decoded as UTF-8 will be skipped.
    """

    for path, dirs, files in os.walk(path):
        for orig_name in files:
            orig_path = os.path.join(path, orig_name)
            try:
                with open(orig_path, "r", encoding="utf-8") as f:
                    orig_content = f.read()
            except UnicodeDecodeError:
                # Probably a binary file; skip it
                continue
            new_name, new_content = process_file(orig_name, orig_content)
            new_path = os.path.join(path, new_name)
            if new_name != orig_name:
                os.rename(orig_path, new_path)
            with open(new_path, "w", encoding="utf-8") as f:
                f.write(new_content)


def process_text_in_zipfile(zf, process_file):
    """Process each file in a zip file using the `process_file` function.

    Returns a new zip file.

    `process_file` should be a function which accepts a filename and content as text
    and returns a (possibly modified) filename and content.  The file will be
    replaced with the new content, and renamed if necessary.

    Files with content that cannot be decoded as UTF-8 will be skipped.
    """

    new_zf = zipfile.ZipFile(io.BytesIO(), "w", zipfile.ZIP_DEFLATED)
    for name in zf.namelist():
        content = zf.read(name)
        try:
            content = content.decode("utf-8")
        except UnicodeDecodeError:
            # Probably a binary file; don't change it
            pass
        else:
            name, content = process_file(name, content)
        # writestr handles either bytes or text, and will implicitly encode text as utf-8
        new_zf.writestr(name, content)
    return new_zf


def inject_namespace(
    name,
    content,
    namespace=None,
    managed=None,
    filename_token=None,
    namespace_token=None,
    namespaced_org=None,
    logger=None,
):
    """ Replaces %%%NAMESPACE%%% in file content and ___NAMESPACE___ in file name
        with either '' if no namespace is provided or 'namespace__' if provided.
    """

    # Handle namespace and filename tokens
    if not filename_token:
        filename_token = "___NAMESPACE___"
    if not namespace_token:
        namespace_token = "%%%NAMESPACE%%%"
    if managed is True and namespace:
        namespace_prefix = namespace + "__"
    else:
        namespace_prefix = ""

    # Handle tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___
    namespaced_org_token = "%%%NAMESPACED_ORG%%%"
    namespaced_org_file_token = "___NAMESPACED_ORG___"
    namespaced_org = namespace_prefix if namespaced_org else ""

    # Handle token %%%NAMESPACE_OR_C%%% for lightning components
    namespace_or_c_token = "%%%NAMESPACE_OR_C%%%"
    namespace_or_c = namespace if managed and namespace else "c"

    # Handle token %%%NAMESPACED_ORG_OR_C%%%
    namespaced_org_or_c_token = "%%%NAMESPACED_ORG_OR_C%%%"
    namespaced_org_or_c = namespace if namespaced_org else "c"

    orig_name = name
    prev_content = content
    content = content.replace(namespace_token, namespace_prefix)
    if logger and content != prev_content:
        logger.info(f'  {name}: Replaced {namespace_token} with "{namespace_prefix}"')

    prev_content = content
    content = content.replace(namespace_or_c_token, namespace_or_c)
    if logger and content != prev_content:
        logger.info(
            f'  {name}: Replaced {namespace_or_c_token} with "{namespace_or_c}"'
        )

    prev_content = content
    content = content.replace(namespaced_org_token, namespaced_org)
    if logger and content != prev_content:
        logger.info(
            f'  {name}: Replaced {namespaced_org_token} with "{namespaced_org}"'
        )

    prev_content = content
    content = content.replace(namespaced_org_or_c_token, namespaced_org_or_c)
    if logger and content != prev_content:
        logger.info(
            f'  {name}: Replaced {namespaced_org_or_c_token} with "{namespaced_org_or_c}"'
        )

    # Replace namespace token in file name
    name = name.replace(filename_token, namespace_prefix)
    name = name.replace(namespaced_org_file_token, namespaced_org)
    if logger and name != orig_name:
        logger.info(f"  {orig_name}: renamed to {name}")

    return name, content


def strip_namespace(name, content, namespace, logger=None):
    """ Given a namespace, strips 'namespace__' from file name and content
    """
    namespace_prefix = "{}__".format(namespace)
    lightning_namespace = "{}:".format(namespace)

    orig_content = content
    new_content = orig_content.replace(namespace_prefix, "")
    new_content = new_content.replace(lightning_namespace, "c:")
    name = name.replace(namespace_prefix, "")
    if orig_content != new_content and logger:
        logger.info(
            "  {file_name}: removed {namespace}".format(
                file_name=name, namespace=namespace_prefix
            )
        )
    return name, new_content


def tokenize_namespace(name, content, namespace, logger=None):
    """ Given a namespace, replaces 'namespace__' with %%%NAMESPACE%%%
    in file content and ___NAMESPACE___ in file name
    """
    if not namespace:
        return name, content

    namespace_prefix = "{}__".format(namespace)
    lightning_namespace = "{}:".format(namespace)

    content = content.replace(namespace_prefix, "%%%NAMESPACE%%%")
    content = content.replace(lightning_namespace, "%%%NAMESPACE_OR_C%%%")
    name = name.replace(namespace_prefix, "___NAMESPACE___")

    return name, content


def zip_clean_metaxml(zip_src, logger=None):
    """ Given a zipfile, cleans all ``*-meta.xml`` files in the zip for
    deployment by stripping all ``<packageVersions/>`` elements
    """
    zip_dest = zipfile.ZipFile(io.BytesIO(), "w", zipfile.ZIP_DEFLATED)
    changed = []
    for name in zip_src.namelist():
        content = zip_src.read(name)
        if name.startswith(META_XML_CLEAN_DIRS) and name.endswith("-meta.xml"):
            try:
                content.decode("utf-8")
            except UnicodeDecodeError:
                # if we cannot decode the content, it may be binary;
                # don't try and replace it.
                pass
            else:
                clean_content = remove_xml_element_string("packageVersions", content)
                if clean_content != content:
                    changed.append(name)
                    content = clean_content
        zip_dest.writestr(name, content)
    if changed and logger:
        logger.info(
            "Cleaned package versions from {} meta.xml files".format(len(changed))
        )
    return zip_dest


def doc_task(task_name, task_config, project_config=None, org_config=None):
    """ Document a (project specific) task configuration in RST format. """
    from cumulusci.core.utils import import_global

    doc = []
    doc.append("{}\n==========================================\n".format(task_name))
    doc.append("**Description:** {}\n".format(task_config.description))
    doc.append("**Class::** {}\n".format(task_config.class_path))

    task_class = import_global(task_config.class_path)
    if "task_docs" in task_class.__dict__:
        task_docs = textwrap.dedent(task_class.task_docs.strip("\n"))
        doc.append(task_docs + "\n")
    if task_class.task_options:
        doc.append("Options:\n------------------------------------------\n")
        defaults = task_config.options or {}
        for name, option in list(task_class.task_options.items()):
            default = defaults.get(name)
            if default:
                default = " **Default: {}**".format(default)
            else:
                default = ""
            if option.get("required"):
                doc.append(
                    "* **{}** *(required)*: {}{}".format(
                        name, option.get("description"), default
                    )
                )
            else:
                doc.append(
                    "* **{}**: {}{}".format(name, option.get("description"), default)
                )

    return "\n".join(doc)


def package_xml_from_dict(items, api_version, package_name=None):
    lines = []

    # Print header
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append('<Package xmlns="http://soap.sforce.com/2006/04/metadata">')

    # Include package name if specified
    if package_name:
        lines.append("    <fullName>{}</fullName>".format(package_name))

    # Print types sections
    for md_type, members in sorted(items.items()):
        members.sort()
        lines.append("    <types>")
        for member in members:
            lines.append("        <members>{}</members>".format(member))
        lines.append("        <name>{}</name>".format(md_type))
        lines.append("    </types>")

    # Print footer
    lines.append("    <version>{0}</version>".format(api_version))
    lines.append("</Package>")

    return "\n".join(lines)


@contextlib.contextmanager
def cd(path):
    """Context manager that changes to another directory
    """
    if not path:
        yield
        return
    cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(cwd)


@contextlib.contextmanager
def temporary_dir(chdir=True):
    """Context manager that creates a temporary directory and chdirs to it.

    When the context manager exits it returns to the previous cwd
    and deletes the temporary directory.
    """
    d = tempfile.mkdtemp()
    try:
        with contextlib.ExitStack() as stack:
            if chdir:
                stack.enter_context(cd(d))
            yield d
    finally:
        if os.path.exists(d):
            shutil.rmtree(d)


def touch(path):
    """Ensure a file exists."""
    with open(path, "a"):
        pass


def in_directory(filepath, dirpath):
    """Returns a boolean for whether filepath is contained in dirpath.

    Normalizes the paths (e.g. resolving symlinks and ..)
    so this is the safe way to make sure a user-configured path
    is located inside the user's project repo.
    """
    filepath = os.path.realpath(filepath)
    dirpath = os.path.realpath(dirpath)
    return filepath == dirpath or filepath.startswith(os.path.join(dirpath, ""))


def log_progress(
    iterable,
    logger,
    batch_size=10000,
    progress_message="Processing... ({})",
    done_message="Done! (Total: {})",
):
    """Log progress while iterating.
    """
    i = 0
    for x in iterable:
        yield x
        i += 1
        if not i % batch_size:
            logger.info(progress_message.format(i))
    logger.info(done_message.format(i))


def random_alphanumeric_underscore(length):
    if sys.version_info[0] >= 3:
        import secrets

        # Ensure the string is the right length
        byte_length = math.ceil((length * 3) / 4)
        return secrets.token_urlsafe(byte_length).replace("-", "_")[:length]
    else:
        import random
        import string

        return "".join(
            random.SystemRandom().choice(
                "_" + string.ascii_uppercase + string.ascii_lowercase + string.digits
            )
            for _ in range(length)
        )


def get_cci_upgrade_command():
    commands_by_path = {
        "cellar": BREW_UPDATE_CMD,
        "linuxbrew": BREW_UPDATE_CMD,
        "pipx": PIPX_UPDATE_CMD,
    }
    for path, cmd in commands_by_path.items():
        if path in CUMULUSCI_PATH.lower():
            return cmd
    return PIP_UPDATE_CMD


def convert_to_snake_case(content):
    s1 = re.sub("([^_])([A-Z][a-z]+)", r"\1_\2", content)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def os_friendly_path(path):
    if os.sep != "/":
        path = path.replace("/", os.sep)
    return path


def get_git_config(config_key):
    p = sarge.Command(
        sarge.shell_format('git config --get "{0!s}"', config_key),
        stderr=sarge.Capture(buffer_size=-1),
        stdout=sarge.Capture(buffer_size=-1),
        shell=True,
    )
    p.run()
    config_value = (
        io.TextIOWrapper(p.stdout, encoding=sys.stdout.encoding).read().strip()
    )

    return config_value if config_value and not p.returncode else None
