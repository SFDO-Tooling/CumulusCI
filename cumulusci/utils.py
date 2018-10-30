from __future__ import unicode_literals
from future import standard_library
from future.utils import text_to_native_str

standard_library.install_aliases()
from builtins import str
from contextlib import contextmanager
import difflib
import fnmatch
import os
import re
import io
import shutil
import zipfile
import tempfile
import textwrap
from datetime import timedelta, datetime

import requests

import xml.etree.ElementTree as ET

CUMULUSCI_PATH = os.path.realpath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
)
META_XML_CLEAN_DIRS = ("classes/", "triggers/", "pages/", "aura/", "components/")
API_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
DATETIME_LEN = len("2018-08-07T16:00:56.000")
UTF8 = text_to_native_str("UTF-8")


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
            with open(filepath) as f:
                s = f.read()
            if max:
                s_updated = s.replace(find, replace, max)
            else:
                s_updated = s.replace(find, replace)
            if s != s_updated:
                if logger:
                    logger.info("Updating {}".format(filepath))
                with open(filepath, "w") as f:
                    f.write(s_updated)


def findReplaceRegex(find, replace, directory, filePattern, logger=None):
    pattern = re.compile(find)
    for path, dirs, files in os.walk(os.path.abspath(directory)):
        for filename in fnmatch.filter(files, filePattern):
            filepath = os.path.join(path, filename)
            with open(filepath) as f:
                s = f.read()
            s_updated = pattern.sub(replace, s)
            if s != s_updated:
                if logger:
                    logger.info("Updating {}".format(filepath))
                with open(filepath, "w") as f:
                    f.write(s_updated)


def findRename(find, replace, directory, logger=None):
    for path, dirs, files in os.walk(os.path.abspath(directory)):
        for filename in files:
            filepath = os.path.join(path, filename)
            if logger:
                logger.info("Renaming {}".format(filepath))
            os.rename(filepath, os.path.join(path, filename.replace(find, replace)))


def elementtree_parse_file(path):
    try:
        tree = ET.parse(path)
    except ET.ParseError as err:
        err.filename = path
        raise err
    return tree


def removeXmlElement(name, directory, file_pattern, logger=None):
    """ Recursively walk a directory and remove XML elements """
    for path, dirs, files in os.walk(os.path.abspath(directory)):
        for filename in fnmatch.filter(files, file_pattern):
            filepath = os.path.join(path, filename)
            remove_xml_element_file(name, filepath)


def remove_xml_element_file(name, path):
    """ Remove XML elements from a single file """
    ET.register_namespace("", "http://soap.sforce.com/2006/04/metadata")
    tree = elementtree_parse_file(path)
    tree = remove_xml_element(name, tree)
    return tree.write(path, encoding=UTF8, xml_declaration=True)


def remove_xml_element_string(name, content):
    """ Remove XML elements from a string """
    ET.register_namespace("", "http://soap.sforce.com/2006/04/metadata")
    tree = ET.fromstring(content)
    tree = remove_xml_element(name, tree)
    clean_content = ET.tostring(tree, encoding=UTF8)
    return clean_content


def remove_xml_element(name, tree):
    """ Removes XML elements from an ElementTree content tree """
    # root = tree.getroot()
    remove = tree.findall(
        ".//{{http://soap.sforce.com/2006/04/metadata}}{}".format(name)
    )
    if not remove:
        return tree

    parent_map = {c: p for p in tree.iter() for c in p}

    for elem in remove:
        parent = parent_map[elem]
        parent.remove(elem)

    return tree


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


def download_extract_github(github_repo, subfolder, ref=None):
    if not ref:
        ref = github_repo.default_branch
    zip_content = io.BytesIO()
    github_repo.archive("zipball", zip_content, ref=ref)
    zip_file = zipfile.ZipFile(zip_content)
    root_folder = sorted(zip_file.namelist())[0]
    subfolder_dir = root_folder + subfolder
    zip_file = zip_subfolder(zip_file, subfolder_dir)
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


def zip_inject_namespace(
    zip_src,
    namespace=None,
    managed=None,
    filename_token=None,
    namespace_token=None,
    namespaced_org=None,
    logger=None,
):
    """ Replaces %%%NAMESPACE%%% for all files and ___NAMESPACE___ in all 
        filenames in the zip with the either '' if no namespace is provided
        or 'namespace__' if provided.
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

    zip_dest = zipfile.ZipFile(io.BytesIO(), "w", zipfile.ZIP_DEFLATED)

    differ = difflib.Differ()

    for name in zip_src.namelist():
        orig_name = str(name)
        content = zip_src.read(name)
        try:
            content = content.decode("utf-8")
        except UnicodeDecodeError:
            # if we cannot decode the content, don't try and replace it.
            pass
        else:
            prev_content = content
            content = content.replace(namespace_token, namespace_prefix)
            if logger and content != prev_content:
                logger.info(
                    '  {}: Replaced %%%NAMESPACE%%% with "{}"'.format(name, namespace)
                )

            prev_content = content
            content = content.replace(namespace_or_c_token, namespace_or_c)
            if logger and content != prev_content:
                logger.info(
                    '  {}: Replaced %%%NAMESPACE_OR_C%%% with "{}"'.format(
                        name, namespace_or_c
                    )
                )

            prev_content = content
            content = content.replace(namespaced_org_token, namespaced_org)
            if logger and content != prev_content:
                logger.info(
                    '  {}: Replaced %%%NAMESPACED_ORG%%% with "{}"'.format(
                        name, namespaced_org
                    )
                )

            prev_content = content
            content = content.replace(namespaced_org_or_c_token, namespaced_org_or_c)
            if logger and content != prev_content:
                logger.info(
                    '  {}: Replaced %%%NAMESPACED_ORG_OR_C%%% with "{}"'.format(
                        name, namespaced_org_or_c
                    )
                )

            content = content.encode("utf-8")

        # Replace namespace token in file name
        name = name.replace(filename_token, namespace_prefix)
        name = name.replace(namespaced_org_file_token, namespaced_org)
        if logger and name != orig_name:
            logger.info("  {}: renamed to {}".format(orig_name, name))
        zip_dest.writestr(name, content)

    return zip_dest


def zip_strip_namespace(zip_src, namespace, logger=None):
    """ Given a namespace, strips 'namespace__' from all files and filenames 
        in the zip 
    """
    namespace_prefix = "{}__".format(namespace)
    lightning_namespace = "{}:".format(namespace)
    zip_dest = zipfile.ZipFile(io.BytesIO(), "w", zipfile.ZIP_DEFLATED)
    for name in zip_src.namelist():
        orig_content = zip_src.read(name)
        try:
            orig_content = orig_content.decode("utf-8")
        except UnicodeDecodeError:
            # if we cannot decode the content, don't try and replace it.
            new_content = orig_content
        else:
            new_content = orig_content.replace(namespace_prefix, "")
            new_content = new_content.replace(lightning_namespace, "c:")
            name = name.replace(namespace_prefix, "")  # not...sure...this..gets...used
            if orig_content != new_content and logger:
                logger.info(
                    "  {file_name}: removed {namespace}".format(
                        file_name=name, namespace=namespace_prefix
                    )
                )
            new_content = new_content.encode("utf-8")

        zip_dest.writestr(name, new_content)
    return zip_dest


def zip_tokenize_namespace(zip_src, namespace, logger=None):
    """ Given a namespace, replaces 'namespace__' with %%%NAMESPACE%%% for all 
        files and ___NAMESPACE___ in all filenames in the zip 
    """
    if not namespace:
        return zip_src

    namespace_prefix = "{}__".format(namespace)
    lightning_namespace = "{}:".format(namespace)
    zip_dest = zipfile.ZipFile(io.BytesIO(), "w", zipfile.ZIP_DEFLATED)
    for name in zip_src.namelist():
        content = zip_src.read(name)
        try:
            content = content.decode("utf-8")
        except UnicodeDecodeError:
            # Probably a binary file; leave it untouched
            pass
        else:
            content = content.replace(namespace_prefix, "%%%NAMESPACE%%%")
            content = content.replace(lightning_namespace, "%%%NAMESPACE_OR_C%%%")
            content = content.encode("utf-8")
            name = name.replace(namespace_prefix, "___NAMESPACE___")
        zip_dest.writestr(name, content)
    return zip_dest


def zip_clean_metaxml(zip_src, logger=None):
    """ Given a zipfile, cleans all *-meta.xml files in the zip for 
        deployment by stripping all <packageVersions/> elements
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
    from cumulusci.core.utils import import_class

    doc = []
    doc.append("{}\n==========================================\n".format(task_name))
    doc.append("**Description:** {}\n".format(task_config.description))
    doc.append("**Class::** {}\n".format(task_config.class_path))

    task_class = import_class(task_config.class_path)
    task_docs = textwrap.dedent(task_class.task_docs.strip("\n"))
    if task_docs:
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


@contextmanager
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


@contextmanager
def temporary_dir():
    """Context manager that creates a temporary directory and chdirs to it.

    When the context manager exits it returns to the previous cwd
    and deletes the temporary directory.
    """
    d = tempfile.mkdtemp()
    try:
        with cd(d):
            yield d
    finally:
        if os.path.exists(d):
            shutil.rmtree(d)


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
