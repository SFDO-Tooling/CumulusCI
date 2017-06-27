import fnmatch
import os
import re
import StringIO
import zipfile

import requests

from xml.etree.ElementTree import ElementTree

CUMULUSCI_PATH = os.path.realpath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')
)


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
                    logger.info('Updating {}'.format(filepath))
                with open(filepath, "w") as f:
                    f.write(s_updated)


def findReplaceRegex(find, replace, directory, filePattern, logger=None):
    for path, dirs, files in os.walk(os.path.abspath(directory)):
        for filename in fnmatch.filter(files, filePattern):
            filepath = os.path.join(path, filename)
            with open(filepath) as f:
                s = f.read()
            s_updated = re.sub(find, replace, s)
            if s != s_updated:
                if logger:
                    logger.info('Updating {}'.format(filepath))
                with open(filepath, "w") as f:
                    f.write(s_updated)


def findRename(find, replace, directory, logger=None):
    for path, dirs, files in os.walk(os.path.abspath(directory)):
        for filename in files:
            filepath = os.path.join(path, filename)
            if logger:
                logger.info('Renaming {}'.format(filepath))
            os.rename(filepath, os.path.join(
                path,
                filename.replace(find, replace),
            ))


def removeXmlElement(name, directory, file_pattern, logger=None):
    for path, dirs, files in os.walk(os.path.abspath(directory)):
        for filename in fnmatch.filter(files, file_pattern):
            filepath = os.path.join(path, filename)
            tree = ElementTree()
            tree.parse(filepath)
            root = tree.getroot()
            remove = root.findall(
                './/{{http://soap.sforce.com/2006/04/metadata}}{}'.format(name)
            )
            if not remove:
                continue

            if logger:
                logger.info(
                    'Modifying {} to remove <{}> elements'.format(
                        filepath,
                        name,
                    )
                )

            parent_map = {c: p for p in tree.iter() for c in p}

            for elem in remove:
                parent = parent_map[elem]
                parent.remove(elem)

            tree.write(
                filepath,
                encoding="UTF-8",
                default_namespace='http://soap.sforce.com/2006/04/metadata',
            )


def download_extract_zip(url, target=None, subfolder=None):
    resp = requests.get(url)
    zip_content = StringIO.StringIO(resp.content)
    zip_file = zipfile.ZipFile(zip_content)
    if subfolder:
        zip_file = zip_subfolder(zip_file, subfolder)
    if target:
        zip_file.extractall(target)
        return
    return zip_file
    


def zip_subfolder(zip_src, path):
    if not path.endswith('/'):
        path = path + '/'

    zip_dest = zipfile.ZipFile(StringIO.StringIO(), 'w', zipfile.ZIP_DEFLATED)
    for name in zip_src.namelist():
        if not name.startswith(path):
            continue

        content = zip_src.read(name)
        rel_name = name.replace(path, '', 1)

        if rel_name:
            zip_dest.writestr(rel_name, content)

    return zip_dest


def zip_inject_namespace(zip_src, namespace=None, managed=None, filename_token=None, namespace_token=None):
    """ Replaces %%%NAMESPACE%%% for all files and ___NAMESPACE___ in all 
        filenames in the zip with the either '' if no namespace is provided
        or 'namespace__' if provided.
    """
    if not filename_token:
        filename_token = '___NAMESPACE___'
    if not namespace_token:
        namespace_token = '%%%NAMESPACE%%%'
    if managed is True and namespace:
        namespace = namespace + '__'
    else:
        namespace = ''

    zip_dest = zipfile.ZipFile(StringIO.StringIO(), 'w', zipfile.ZIP_DEFLATED)
    for name in zip_src.namelist():
        content = zip_src.read(name).replace(namespace_token, namespace)
        name = name.replace(filename_token, namespace)
        zip_dest.writestr(name, content)
    return zip_dest

def zip_strip_namespace(zip_src, namespace):
    """ Given a namespace, strips 'namespace__' from all files and filenames 
        in the zip 
    """
    namespace_prefix = '{}__'.format(namespace)
    zip_dest = zipfile.ZipFile(StringIO.StringIO(), 'w', zipfile.ZIP_DEFLATED)
    for name in zip_src.namelist():
        content = zip_src.read(name).replace(namespace_prefix, '')
        name = name.replace(namespace_prefix, '')
        zip_dest.writestr(name, content)
    return zip_dest

def zip_tokenize_namespace(zip_src, namespace):
    """ Given a namespace, replaces 'namespace__' with %%%NAMESPACE%%% for all 
        files and ___NAMESPACE___ in all filenames in the zip 
    """
    if not namespace:
        return zip_dest

    namespace_prefix = '{}__'.format(namespace)
    zip_dest = zipfile.ZipFile(StringIO.StringIO(), 'w', zipfile.ZIP_DEFLATED)
    for name in zip_src.namelist():
        content = zip_src.read(name).replace(namespace_prefix, '%%%NAMESPACE%%%')
        name = name.replace(namespace_prefix, '___NAMESPACE___')
        zip_dest.writestr(name, content)
    return zip_dest

def doc_task(task_name, task_config, project_config=None, org_config=None):
    """ Document a (project specific) task configuration in RST format. """
    from cumulusci.core.utils import import_class
    doc = []
    doc.append(
        '{}\n==========================================\n'.format(task_name))
    doc.append('**Description:** {}\n'.format(task_config.description))
    doc.append('**Class::** {}\n'.format(task_config.class_path))

    task_class = import_class(task_config.class_path)
    if task_class.task_options:
        doc.append('Options:\n------------------------------------------\n')
        defaults = task_config.options
        if not defaults:
            defaults = {}
        for name, option in task_class.task_options.items():
            default = defaults.get(name)
            if default:
                default = ' **Default: {}**'.format(default)
            else:
                default = ''
            if option.get('required'):
                doc.append('* **{}** *(required)*: {}{}'.format(
                    name,
                    option.get('description'),
                    default))
            else:
                doc.append('* **{}**: {}{}'.format(
                    name,
                    option.get('description'),
                    default))

    return '\n'.join(doc)


def package_xml_from_dict(items, api_version, package_name=None):
    lines = []

    # Print header
    lines.append(u'<?xml version="1.0" encoding="UTF-8"?>')
    lines.append(u'<Package xmlns="http://soap.sforce.com/2006/04/metadata">')

    # Include package name if specified
    if package_name:
        lines.append('    <fullName>{}</fullName'.format(package_name))

    # Print types sections
    md_types = items.keys()
    md_types.sort()
    for md_type in md_types:
        members = items[md_type]
        members.sort()
        lines.append('    <types>')
        for member in members:
            lines.append('        <members>{}</members>'.format(member))
        lines.append('        <name>{}</name>'.format(md_type))
        lines.append('    </types>')

    # Print footer
    lines.append(u'    <version>{0}</version>'.format(api_version))
    lines.append(u'</Package>')

    return u'\n'.join(lines)
