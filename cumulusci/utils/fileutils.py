from pathlib import Path
from urllib.request import urlopen


def _get_path_from_stream(stream):
    stream_name = getattr(stream, "name", None)
    if stream_name:
        path = Path(stream.name).absolute()
    else:
        path = "<stream>"
    return str(path)


def load_from_source(source, loader):
    if hasattr(source, "read"):  # open file-like
        data = loader(source)
        path = _get_path_from_stream(source)
    elif hasattr(source, "open"):  # path-like
        with source.open() as f:
            data = loader(f)
            path = str(source)
    elif "://" in source:  # URL string-like
        url = source
        with urlopen(url) as f:
            data = loader(f)
            path = url
    else:  # path string-like
        path = source
        with open(path) as f:
            data = loader(f)
    return path, data
