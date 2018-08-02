
import io
import os
import base64
import zipfile


class BasePackageZipBuilder(object):
    def __init__(self):
        self._stream = None
        self.zip = None

    def _open_zip(self):
        self._stream = io.BytesIO()
        self.zip = zipfile.ZipFile(self._stream, 'w', zipfile.ZIP_DEFLATED)

    def _write_package_xml(self, package_xml):
        self._write_file('package.xml', package_xml)

    def _write_file(self, path, content):
        self.zip.writestr(path, content)

    def _encode_zip(self):
        if not self.zip.fp:
            raise RuntimeError('Attempt to encode a file that was already closed')
        self.zip.close()
        return base64.b64encode(self._stream.getvalue())

class CallablePackageZipBuilder(BasePackageZipBuilder):
    def __call__(self):
        self._open_zip()
        self._populate_zip()
        return self._encode_zip()

    def _populate_zip(self):
        raise NotImplementedError('Subclasses need to provide their own implementation')

class FilePackageZipBuilder(BasePackageZipBuilder):
    """ Builds a package.zip from a given MDAPI formatted source tree """
    def __init__(self, path):
        super(FilePackageZipBuilder, self).__init__()
        self.path = path

"""
get a path
find all members
generate a packagexml
load members into zipfile
encode the zipfile
"""


class MetadataProcessor(object):
    """
    MetadataProcessor allows a caller (task) to:
    - walk a metadata tree (presumably on the filesystem)
    - process each item (for example to remove a version dependency) with pre-registered processors
    - get back a zipfile ready for the salesforce metadata api

    This lets us replace core functionality of utils, as well as packagezipbuilder.
    """

    def process(self):
        for root, dirs, files in os.walk(self.path):

            for fname in files:

                fpath = os.path.join(root, fname)
