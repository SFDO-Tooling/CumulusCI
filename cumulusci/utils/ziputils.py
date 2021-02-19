import hashlib
import io
import zipfile


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
    zf.close()
    return new_zf


def hash_zipfile_contents(zf):
    """Returns a hash of a zipfile's file contents.

    Ignores things like file mode, modtime
    """
    h = hashlib.blake2b()
    for name in zf.namelist():
        h.update(name.encode("utf-8"))
        h.update(zf.read(name))
    return h.hexdigest()
