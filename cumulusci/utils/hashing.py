import hashlib
import json
from pydantic import BaseModel


def cci_json_encoder(obj):
    if isinstance(obj, BaseModel):
        return obj.dict()
    if hasattr(obj, "task_config"):
        if obj.skip:
            return None
        return obj.task_config
    # Fallback to default encoder
    try:
        return json.JSONEncoder().default(obj)
    except TypeError:
        raise TypeError(
            f"Object of type {obj.__class__.__name__} is not JSON serializable"
        )


def hash_dict(dictionary):
    # Step 1: Serialize the dictionary in a sorted order to ensure consistency
    serialized_dict = json.dumps(
        dictionary, sort_keys=True, default=cci_json_encoder
    ).encode("utf-8")

    # Step 2: Create an MD5 hash of the serialized dictionary
    md5_hash = hashlib.md5(serialized_dict).hexdigest()

    return md5_hash[:8]
