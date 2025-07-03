from cumulusci.core.exceptions import CumulusCIException


class AbstractCommitDir(object):
    """
    Abstract class for commit directories.
    """

    pass


def get_ref_from_options(project_config, options: dict) -> str:
    if "ref" in options:
        return options["ref"]

    elif "version" in options:
        get_beta = options.get("version") == "latest_beta"
        tag_name = project_config.get_latest_tag(beta=get_beta)
        return f"tags/{tag_name}"

    elif "tag_name" in options:
        if options["tag_name"] in ("latest", "latest_beta"):
            get_beta = options["tag_name"] == "latest_beta"
            tag_name = project_config.get_latest_tag(beta=get_beta)
        else:
            tag_name = options["tag_name"]

        return f"tags/{tag_name}"

    else:
        raise CumulusCIException("No ref, version, or tag_name present")
