from pickle import PickleError, loads


def load_decrypted_config_from_bytes(b: bytes) -> object:
    assert isinstance(b, bytes)

    try:
        data = loads(b, encoding="bytes")
    except PickleError as e:
        # we use ValueError because Pickle and Crypto both do too
        raise ValueError(str(e)) from e
    return data
