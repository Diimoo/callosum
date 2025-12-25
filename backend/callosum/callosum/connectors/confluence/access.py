from collections.abc import Callable
from typing import Any
from typing import cast

from callosum.access.models import ExternalAccess
from callosum.connectors.confluence.callosum_confluence import CallosumConfluence
from callosum.utils.variable_functionality import fetch_versioned_implementation
from callosum.utils.variable_functionality import global_version


def get_page_restrictions(
    confluence_client: CallosumConfluence,
    page_id: str,
    page_restrictions: dict[str, Any],
    ancestors: list[dict[str, Any]],
) -> ExternalAccess | None:
    """
    Get page access restrictions for a Confluence page.
    This functionality requires Enterprise Edition.

    Args:
        confluence_client: CallosumConfluence client instance
        page_id: The ID of the page
        page_restrictions: Dictionary containing page restriction data
        ancestors: List of ancestor pages with their restriction data

    Returns:
        ExternalAccess object for the page. None if EE is not enabled or no restrictions found.
    """
    # Check if EE is enabled
    if not global_version.is_ee_version():
        return None

    # Fetch the EE implementation
    ee_get_all_page_restrictions = cast(
        Callable[
            [CallosumConfluence, str, dict[str, Any], list[dict[str, Any]]],
            ExternalAccess | None,
        ],
        fetch_versioned_implementation(
            "callosum.external_permissions.confluence.page_access", "get_page_restrictions"
        ),
    )

    return ee_get_all_page_restrictions(
        confluence_client, page_id, page_restrictions, ancestors
    )


def get_all_space_permissions(
    confluence_client: CallosumConfluence,
    is_cloud: bool,
) -> dict[str, ExternalAccess]:
    """
    Get access permissions for all spaces in Confluence.
    This functionality requires Enterprise Edition.

    Args:
        confluence_client: CallosumConfluence client instance
        is_cloud: Whether this is a Confluence Cloud instance

    Returns:
        Dictionary mapping space keys to ExternalAccess objects. Empty dict if EE is not enabled.
    """
    # Check if EE is enabled
    if not global_version.is_ee_version():
        return {}

    # Fetch the EE implementation
    ee_get_all_space_permissions = cast(
        Callable[
            [CallosumConfluence, bool],
            dict[str, ExternalAccess],
        ],
        fetch_versioned_implementation(
            "callosum.external_permissions.confluence.space_access",
            "get_all_space_permissions",
        ),
    )

    return ee_get_all_space_permissions(confluence_client, is_cloud)
