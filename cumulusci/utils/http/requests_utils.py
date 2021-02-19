from json import JSONDecodeError

from cumulusci.core.exceptions import CumulusCIException


def safe_json_from_response(response):
    "Check JSON response is HTTP200 and actually JSON."
    response.raise_for_status()

    try:
        return response.json()
    except JSONDecodeError:
        raise CumulusCIException(f"Cannot decode as JSON:  {response.text}")
