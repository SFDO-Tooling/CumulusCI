from typing import Optional


def format_subscriber_package_version_where_clause(
    spv_id: str, install_key: Optional[str] = None
) -> str:
    """Get the where clause for a SubscriberPackageVersion query

    Does not include the WHERE.
    Includes the installation key if provided.
    """
    where_clause = f"Id='{spv_id}'"

    if install_key:
        where_clause += f" AND InstallationKey ='{install_key}'"

    return where_clause
