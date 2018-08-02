
import io
import os
import base64
import zipfile

from cumulusci.utils import memoize


def files_from_path(rootDir):
    """ list all the files in rootDir, with their path relative to rootDir."""

    # stolen from stackexchange.... its a gnarly list comprehension but
    # pythons like, designed to work this way somehow.
    # https://stackoverflow.com/questions/1192978/python-get-relative-path-of-all-files-and-subfolders-in-a-directory

    return [os.path.relpath(os.path.join(dirpath, fname), rootDir)
            for (dirpath, _, filenames)
            in os.walk(rootDir)
            for fname in filenames]


class BasePackageZipBuilder(object):
    def __init__(self, stream=None):
        if stream is None:
            stream = io.BytesIO()
        self._stream = stream
        self.zip = None
        self.built = False

    def _open_zip(self):
        self.zip = zipfile.ZipFile(self._stream, 'w', zipfile.ZIP_DEFLATED)

    def _close_zip(self):
        self.zip.close()

    def _write_package_xml(self, package_xml):
        self._write_file('package.xml', package_xml)

    def _write_file(self, path, content):
        if self.zip is None:
            raise RuntimeError('Attempt to write without opening the zip.')
        self.zip.writestr(path, content)

    def _encode_zip(self):
        if not self.built:
            raise RuntimeError(
                'Attempt to encode a zip that was not built')
        return base64.b64encode(self._stream.getvalue())

    def _populate_zip(self):
        raise NotImplementedError(
            'Subclasses need to provide their own implementation')

    def _build_zip(self):
        if self.built:
            raise RuntimeError('Zip already built.')
        self._open_zip()
        self._populate_zip()
        self._close_zip()
        self.built = True

    def encode_zip(self, b64=True):
        """ build and encode the zipfile. default to base64 encoding, but raw bytes available """
        if not self.built:
            self._build_zip()
        if not b64:
            return self._stream.getvalue()
        return self._encode_zip()


class CallablePackageZipBuilder(BasePackageZipBuilder):
    def __call__(self):
        return self.encode_zip()


class FilePackageZipBuilder(BasePackageZipBuilder):
    """ Builds a package.zip from a given MDAPI formatted source tree """

    def __init__(self, path):
        super(FilePackageZipBuilder, self).__init__()
        self.path = path

    @property
    @memoize
    def _file_list(self):
        return [f for f in files_from_path(self.path) if not os.path.basename(f).startswith('.')]

    @property
    @memoize
    def _contents(self):
        retval = {}
        for filename in self._file_list:
            with open(os.path.join(self.path, filename), 'r') as f:
                retval[filename] = f.read()
        return retval

    def _populate_zip(self):
        for filename in self._file_list:
            self._write_file(filename, self._contents[filename])
