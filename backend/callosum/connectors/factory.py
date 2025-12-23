from typing import Any
from typing import Type

from sqlalchemy.orm import Session

from callosum.configs.constants import DocumentSource
from callosum.configs.constants import DocumentSourceRequiringTenantContext
from callosum.connectors.airtable.airtable_connector import AirtableConnector
from callosum.connectors.asana.connector import AsanaConnector
from callosum.connectors.axero.connector import AxeroConnector
from callosum.connectors.blob.connector import BlobStorageConnector
from callosum.connectors.bookstack.connector import BookstackConnector
from callosum.connectors.clickup.connector import ClickupConnector
from callosum.connectors.confluence.connector import ConfluenceConnector
from callosum.connectors.discord.connector import DiscordConnector
from callosum.connectors.discourse.connector import DiscourseConnector
from callosum.connectors.document360.connector import Document360Connector
from callosum.connectors.dropbox.connector import DropboxConnector
from callosum.connectors.egnyte.connector import EgnyteConnector
from callosum.connectors.file.connector import LocalFileConnector
from callosum.connectors.fireflies.connector import FirefliesConnector
from callosum.connectors.freshdesk.connector import FreshdeskConnector
from callosum.connectors.github.connector import GithubConnector
from callosum.connectors.gitlab.connector import GitlabConnector
from callosum.connectors.gmail.connector import GmailConnector
from callosum.connectors.gong.connector import GongConnector
from callosum.connectors.google_drive.connector import GoogleDriveConnector
from callosum.connectors.google_site.connector import GoogleSitesConnector
from callosum.connectors.guru.connector import GuruConnector
from callosum.connectors.hubspot.connector import HubSpotConnector
from callosum.connectors.interfaces import BaseConnector
from callosum.connectors.interfaces import EventConnector
from callosum.connectors.interfaces import LoadConnector
from callosum.connectors.interfaces import PollConnector
from callosum.connectors.linear.connector import LinearConnector
from callosum.connectors.loopio.connector import LoopioConnector
from callosum.connectors.mediawiki.wiki import MediaWikiConnector
from callosum.connectors.models import InputType
from callosum.connectors.notion.connector import NotionConnector
from callosum.connectors.callosum_jira.connector import JiraConnector
from callosum.connectors.productboard.connector import ProductboardConnector
from callosum.connectors.salesforce.connector import SalesforceConnector
from callosum.connectors.sharepoint.connector import SharepointConnector
from callosum.connectors.slab.connector import SlabConnector
from callosum.connectors.slack.connector import SlackPollConnector
from callosum.connectors.teams.connector import TeamsConnector
from callosum.connectors.web.connector import WebConnector
from callosum.connectors.wikipedia.connector import WikipediaConnector
from callosum.connectors.xenforo.connector import XenforoConnector
from callosum.connectors.zendesk.connector import ZendeskConnector
from callosum.connectors.zulip.connector import ZulipConnector
from callosum.db.credentials import backend_update_credential_json
from callosum.db.models import Credential


class ConnectorMissingException(Exception):
    pass


def identify_connector_class(
    source: DocumentSource,
    input_type: InputType | None = None,
) -> Type[BaseConnector]:
    connector_map = {
        DocumentSource.WEB: WebConnector,
        DocumentSource.FILE: LocalFileConnector,
        DocumentSource.SLACK: {
            InputType.POLL: SlackPollConnector,
            InputType.SLIM_RETRIEVAL: SlackPollConnector,
        },
        DocumentSource.GITHUB: GithubConnector,
        DocumentSource.GMAIL: GmailConnector,
        DocumentSource.GITLAB: GitlabConnector,
        DocumentSource.GOOGLE_DRIVE: GoogleDriveConnector,
        DocumentSource.BOOKSTACK: BookstackConnector,
        DocumentSource.CONFLUENCE: ConfluenceConnector,
        DocumentSource.JIRA: JiraConnector,
        DocumentSource.PRODUCTBOARD: ProductboardConnector,
        DocumentSource.SLAB: SlabConnector,
        DocumentSource.NOTION: NotionConnector,
        DocumentSource.ZULIP: ZulipConnector,
        DocumentSource.GURU: GuruConnector,
        DocumentSource.LINEAR: LinearConnector,
        DocumentSource.HUBSPOT: HubSpotConnector,
        DocumentSource.DOCUMENT360: Document360Connector,
        DocumentSource.GONG: GongConnector,
        DocumentSource.GOOGLE_SITES: GoogleSitesConnector,
        DocumentSource.ZENDESK: ZendeskConnector,
        DocumentSource.LOOPIO: LoopioConnector,
        DocumentSource.DROPBOX: DropboxConnector,
        DocumentSource.SHAREPOINT: SharepointConnector,
        DocumentSource.TEAMS: TeamsConnector,
        DocumentSource.SALESFORCE: SalesforceConnector,
        DocumentSource.DISCOURSE: DiscourseConnector,
        DocumentSource.AXERO: AxeroConnector,
        DocumentSource.CLICKUP: ClickupConnector,
        DocumentSource.MEDIAWIKI: MediaWikiConnector,
        DocumentSource.WIKIPEDIA: WikipediaConnector,
        DocumentSource.ASANA: AsanaConnector,
        DocumentSource.S3: BlobStorageConnector,
        DocumentSource.R2: BlobStorageConnector,
        DocumentSource.GOOGLE_CLOUD_STORAGE: BlobStorageConnector,
        DocumentSource.OCI_STORAGE: BlobStorageConnector,
        DocumentSource.XENFORO: XenforoConnector,
        DocumentSource.DISCORD: DiscordConnector,
        DocumentSource.FRESHDESK: FreshdeskConnector,
        DocumentSource.FIREFLIES: FirefliesConnector,
        DocumentSource.EGNYTE: EgnyteConnector,
        DocumentSource.AIRTABLE: AirtableConnector,
    }
    connector_by_source = connector_map.get(source, {})

    if isinstance(connector_by_source, dict):
        if input_type is None:
            # If not specified, default to most exhaustive update
            connector = connector_by_source.get(InputType.LOAD_STATE)
        else:
            connector = connector_by_source.get(input_type)
    else:
        connector = connector_by_source
    if connector is None:
        raise ConnectorMissingException(f"Connector not found for source={source}")

    if any(
        [
            input_type == InputType.LOAD_STATE
            and not issubclass(connector, LoadConnector),
            input_type == InputType.POLL and not issubclass(connector, PollConnector),
            input_type == InputType.EVENT and not issubclass(connector, EventConnector),
        ]
    ):
        raise ConnectorMissingException(
            f"Connector for source={source} does not accept input_type={input_type}"
        )
    return connector


def instantiate_connector(
    db_session: Session,
    source: DocumentSource,
    input_type: InputType,
    connector_specific_config: dict[str, Any],
    credential: Credential,
    tenant_id: str | None = None,
) -> BaseConnector:
    connector_class = identify_connector_class(source, input_type)

    if source in DocumentSourceRequiringTenantContext:
        connector_specific_config["tenant_id"] = tenant_id

    connector = connector_class(**connector_specific_config)
    new_credentials = connector.load_credentials(credential.credential_json)

    if new_credentials is not None:
        backend_update_credential_json(credential, new_credentials, db_session)

    return connector
