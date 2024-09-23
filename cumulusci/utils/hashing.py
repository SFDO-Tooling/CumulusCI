import hashlib
import json
import asyncio
from pathlib import Path, PosixPath
import aiofiles


def cci_json_encoder(obj):
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "task_config"):
        if obj.skip:
            return None
        return obj.task_config
    if isinstance(obj, Path | PosixPath):
        return str(obj)
    # Fallback to default encoder
    try:
        return json.JSONEncoder().default(obj)
    except TypeError:
        raise TypeError(
            f"Object of type {obj.__class__.__name__} is not JSON serializable"
        )


def compute_hash(chunks):
    md5_hash = hashlib.md5()
    for chunk in chunks:
        md5_hash.update(chunk)
    return md5_hash.hexdigest()[:8]


def hash_as_json(data):
    # Step 1: Serialize the dictionary in a sorted order to ensure consistency
    serialized_dict = json.dumps(data, sort_keys=True, default=cci_json_encoder).encode(
        "utf-8"
    )
    return compute_hash([serialized_dict])


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
