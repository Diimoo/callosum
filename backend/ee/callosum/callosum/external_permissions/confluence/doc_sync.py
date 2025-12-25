"""
Rules defined here:
https://confluence.atlassian.com/conf85/check-who-can-view-a-page-1283360557.html
"""

from collections.abc import Generator

from ee.callosum.external_permissions.perm_sync_types import FetchAllDocumentsFunction
from ee.callosum.external_permissions.perm_sync_types import FetchAllDocumentsIdsFunction
from ee.callosum.external_permissions.utils import generic_doc_sync
from callosum.access.models import DocExternalAccess
from callosum.configs.constants import DocumentSource
from callosum.connectors.confluence.connector import ConfluenceConnector
from callosum.connectors.credentials_provider import CallosumDBCredentialsProvider
from callosum.db.models import ConnectorCredentialPair
from callosum.indexing.indexing_heartbeat import IndexingHeartbeatInterface
from callosum.utils.logger import setup_logger
from shared_configs.contextvars import get_current_tenant_id

logger = setup_logger()


CONFLUENCE_DOC_SYNC_LABEL = "confluence_doc_sync"


def confluence_doc_sync(
    cc_pair: ConnectorCredentialPair,
    fetch_all_existing_docs_fn: FetchAllDocumentsFunction,
    fetch_all_existing_docs_ids_fn: FetchAllDocumentsIdsFunction,
    callback: IndexingHeartbeatInterface | None,
) -> Generator[DocExternalAccess, None, None]:
    """
    Fetches document permissions from Confluence and yields DocExternalAccess objects.
    Compares fetched documents against existing documents in the DB for the connector.
    If a document exists in the DB but not in the Confluence fetch, it's marked as restricted.
    """
    confluence_connector = ConfluenceConnector(
        **cc_pair.connector.connector_specific_config
    )

    provider = CallosumDBCredentialsProvider(
        get_current_tenant_id(), "confluence", cc_pair.credential_id
    )
    confluence_connector.set_credentials_provider(provider)

    yield from generic_doc_sync(
        cc_pair=cc_pair,
        fetch_all_existing_docs_ids_fn=fetch_all_existing_docs_ids_fn,
        callback=callback,
        doc_source=DocumentSource.CONFLUENCE,
        slim_connector=confluence_connector,
        label=CONFLUENCE_DOC_SYNC_LABEL,
    )
