import aiofiles
import hashlib
import json
import asyncio
from io import BytesIO
from pathlib import Path, PosixPath
from collections.abc import Iterable
from cumulusci.utils.serialization import (
    encode_value,
    decode_dict,
    decode_nested_dict,
    json_dumps,
)


def compute_hash(chunks):
    if isinstance(chunks, str):
        chunks = BytesIO(chunks.encode("utf-8"))
    if isinstance(chunks, bytes):
        chunks = BytesIO(chunks)
    md5_hash = hashlib.md5()
    for chunk in chunks:
        md5_hash.update(chunk)
    return md5_hash.hexdigest()[:8]


def dump_json(data, **kwargs):
    # NOTE: This means that dict ordering is not respected by the hash
    # This is a tradeoff to ensure that the hash is consistent across Python versions
    # and that the hash is not affected by changes in the order of the keys in the dictionary
    # If you need ordering, pass in a list of dictionaries
    kwargs.setdefault("sort_keys", True)
    return json_dumps(data).encode("utf-8")


def hash_as_json(data):
    try:
        # if isinstance(data, dict):
        #     # Convert the dictionary to a list of dictionaries to ensure consistent ordering
        #     hash_data = [{k, v} for k, v in data.items()]
        hash_content = dump_json(data)
        hashed = compute_hash(hash_content)
    except TypeError as e:
        import pdb

        pdb.set_trace()
        raise ValueError(f"Data {data} is not JSON serializable")
    return hashed


def hash_file(file):
    with open(file, "rb") as f:
        return compute_hash(iter(lambda: f.read(4096), b""))


def hash_stream(stream):
    # Step 1: Read the stream in chunks to avoid loading the entire stream into memory
    return compute_hash(stream)


async def async_hash_file(file):
    async with aiofiles.open(file, "rb") as f:
        chunks = []
        while True:
            chunk = await f.read(4096)
            if not chunk:
                break
            chunks.append(chunk)
        return compute_hash(chunks)


async def async_gather_hashes(files):
    return await asyncio.gather(*(async_hash_file(file) for file in files))


def gather_files(directory):
    return [file for file in directory.rglob("*") if file.is_file()]


def hash_directory(directory):
    # Convert directory to Path object
    directory = Path(directory)

    # Step 1: Gather all files in the directory and its subdirectories
    files = gather_files(directory)

    # Step 2: Sort the list of files to ensure consistency
    files.sort()

    # Step 3: Use asyncio to gather file hashes in parallel
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    file_hashes = loop.run_until_complete(async_gather_hashes(files))
    loop.close()

    # Step 4: Create an MD5 hash of the concatenated MD5 hashes of each file
    md5_hash = hashlib.md5()
    for file_hash in file_hashes:
        md5_hash.update(file_hash.encode())

    return md5_hash.hexdigest()[:8]


def hash_obj(obj):
    if isinstance(obj, Path):
        if obj.is_file():
            return hash_file(obj)
        elif obj.is_dir():
            return hash_directory(obj)
        else:
            raise ValueError(f"Path {obj} is not a file or directory")
    return hash_as_json(obj)
