"""Process environment variables and global configurations for some options.

Returns option values in the following order of precedence:
1. Environment variables
2. Global configuration options
3. Click Option
"""

import os

from cumulusci.core.config import BaseGlobalConfig

# CLI Environment Variables
NO_PROMPT_ENV = "CUMULUSCI_NO_PROMPT"
PLAIN_OUTPUT_ENV = "CUMULUSCI_PLAIN_OUTPUT"


def no_prompt_callback(ctx, param, value):
    """Process the "No Prompt". output global setting."""
    print(param)
    global_config = BaseGlobalConfig()
    global_value = global_config.cli__no_prompt
    return _select_value(NO_PROMPT_ENV, global_value, value)


def plain_output_callback(ctx, param, value):
    """Process the Plain Table output global setting."""
    global_config = BaseGlobalConfig()
    global_value = global_config.cli__plain_output
    return _select_value(PLAIN_OUTPUT_ENV, global_value, value)


def _select_value(env_var, global_value, value):
    """Returns the option value in the order of precedence."""
    if env_var in os.environ:
        return os.environ[env_var]
    elif global_value is not None:
        return global_value
    else:
        return value
