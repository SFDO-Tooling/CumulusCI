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

def findReplace(directory, find, replace, filePattern, logger=None):
    for path, dirs, files in os.walk(os.path.abspath(directory)):
        for filename in fnmatch.filter(files, filePattern):
            filepath = os.path.join(path, filename)
            with open(filepath) as f:
                s = f.read()
            s_updated = s.replace(find, replace)
            if s != s_updated:
                if logger:
                    logger.info('Updating {}'.format(filepath))
                with open(filepath, "w") as f:
                    f.write(s_updated)

def findReplaceRegex(directory, find, replace, filePattern, logger=None):
    for path, dirs, files in os.walk(os.path.abspath(directory)):
        for filename in fnmatch.filter(files, filePattern):
            filepath = os.path.join(path, filename)
            with open(filepath) as f:
                s = f.read()
            s = s.replace(find, replace)
            s_updated = re.sub(find, replace, s)
            if s != s_updated:
                if logger:
                    logger.info('Updating {}'.format(filepath))
                with open(filepath, "w") as f:
                    f.write(s)

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
