"""Process environment variables and global configurations for some options.

Returns option values in the following order of precedence:
1. Global configuration options
2. Click Option
3. Environment variables
4. Click Option default value
"""


from cumulusci.core.config import BaseGlobalConfig

# CLI Environment Variables
CCI_ENV_PREFIX = "CCI__"
CLI_ENV_PREFIX = CCI_ENV_PREFIX + "CLI__"
NO_PROMPT_ENV = CLI_ENV_PREFIX + "ALWAYS_RECREATE"
PLAIN_OUTPUT_ENV = CLI_ENV_PREFIX + "PLAIN_OUTPUT"


def global_option_lookup(ctx, param, value):
    """Process Click Option and return global config setting, if it exists."""
    global_attr = param.envvar.replace(CCI_ENV_PREFIX, "").lower()
    global_config = BaseGlobalConfig()
    global_value = getattr(global_config, global_attr)
    if global_value is not None:
        return global_value
    else:
        return value
