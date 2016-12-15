import fnmatch
import os
import re
import StringIO
import zipfile

CUMULUSCI_PATH = os.path.realpath(
    os.path.join(
        os.path.dirname(
            os.path.realpath(__file__),
        ),
        '..'
    )
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
                    
def findRename(find,replace,directory,logger=None):
    for path, dirs, files in os.walk(os.path.abspath(directory)):
        for filename in files:
            filepath = os.path.join(path, filename)
            if logger:
                logger.info('Renaming {}'.format(filepath))
            os.rename(filepath, os.path.join(path,filename.replace(find,replace)))

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

def doc_task(task_name, task_config, project_config=None, org_config=None):
    from cumulusci.core.utils import import_class
    doc = []
    doc.append('{}\n==========================================\n'.format(task_name))
    doc.append('**Description:** {}\n'.format(task_config.description))
    doc.append('**Class::** {}\n'.format(task_config.class_path))

    task_class = import_class(task_config.class_path)
    if task_class.task_options:
        doc.append('Options:\n------------------------------------------\n')
        defaults = task_config.options
        if not defaults:
            defaults = {}
        for name, option in task_class.task_options.items():
            default = defaults.get('name')
            if default:
                default = ' **Default: {}**'.format(default)
            else:
                default = ''
            if option.get('required'):
                doc.append('* **{}** *(required)*: {}{}'.format(name, option.get('description'), default))
            else:
                doc.append('* **{}**: {}{}'.format(name, option.get('description'), default))

    return '\n'.join(doc)
