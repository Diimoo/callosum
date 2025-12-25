"""Registry mapping for connector classes."""

from pydantic import BaseModel

from callosum.configs.constants import DocumentSource


class ConnectorMapping(BaseModel):
    module_path: str
    class_name: str


# Mapping of DocumentSource to connector details for lazy loading
CONNECTOR_CLASS_MAP = {
    DocumentSource.WEB: ConnectorMapping(
        module_path="callosum.connectors.web.connector",
        class_name="WebConnector",
    ),
    DocumentSource.FILE: ConnectorMapping(
        module_path="callosum.connectors.file.connector",
        class_name="LocalFileConnector",
    ),
    DocumentSource.SLACK: ConnectorMapping(
        module_path="callosum.connectors.slack.connector",
        class_name="SlackConnector",
    ),
    DocumentSource.GITHUB: ConnectorMapping(
        module_path="callosum.connectors.github.connector",
        class_name="GithubConnector",
    ),
    DocumentSource.GMAIL: ConnectorMapping(
        module_path="callosum.connectors.gmail.connector",
        class_name="GmailConnector",
    ),
    DocumentSource.GITLAB: ConnectorMapping(
        module_path="callosum.connectors.gitlab.connector",
        class_name="GitlabConnector",
    ),
    DocumentSource.GITBOOK: ConnectorMapping(
        module_path="callosum.connectors.gitbook.connector",
        class_name="GitbookConnector",
    ),
    DocumentSource.GOOGLE_DRIVE: ConnectorMapping(
        module_path="callosum.connectors.google_drive.connector",
        class_name="GoogleDriveConnector",
    ),
    DocumentSource.BOOKSTACK: ConnectorMapping(
        module_path="callosum.connectors.bookstack.connector",
        class_name="BookstackConnector",
    ),
    DocumentSource.OUTLINE: ConnectorMapping(
        module_path="callosum.connectors.outline.connector",
        class_name="OutlineConnector",
    ),
    DocumentSource.CONFLUENCE: ConnectorMapping(
        module_path="callosum.connectors.confluence.connector",
        class_name="ConfluenceConnector",
    ),
    DocumentSource.JIRA: ConnectorMapping(
        module_path="callosum.connectors.jira.connector",
        class_name="JiraConnector",
    ),
    DocumentSource.PRODUCTBOARD: ConnectorMapping(
        module_path="callosum.connectors.productboard.connector",
        class_name="ProductboardConnector",
    ),
    DocumentSource.SLAB: ConnectorMapping(
        module_path="callosum.connectors.slab.connector",
        class_name="SlabConnector",
    ),
    DocumentSource.CODA: ConnectorMapping(
        module_path="callosum.connectors.coda.connector",
        class_name="CodaConnector",
    ),
    DocumentSource.NOTION: ConnectorMapping(
        module_path="callosum.connectors.notion.connector",
        class_name="NotionConnector",
    ),
    DocumentSource.ZULIP: ConnectorMapping(
        module_path="callosum.connectors.zulip.connector",
        class_name="ZulipConnector",
    ),
    DocumentSource.GURU: ConnectorMapping(
        module_path="callosum.connectors.guru.connector",
        class_name="GuruConnector",
    ),
    DocumentSource.LINEAR: ConnectorMapping(
        module_path="callosum.connectors.linear.connector",
        class_name="LinearConnector",
    ),
    DocumentSource.HUBSPOT: ConnectorMapping(
        module_path="callosum.connectors.hubspot.connector",
        class_name="HubSpotConnector",
    ),
    DocumentSource.DOCUMENT360: ConnectorMapping(
        module_path="callosum.connectors.document360.connector",
        class_name="Document360Connector",
    ),
    DocumentSource.GONG: ConnectorMapping(
        module_path="callosum.connectors.gong.connector",
        class_name="GongConnector",
    ),
    DocumentSource.GOOGLE_SITES: ConnectorMapping(
        module_path="callosum.connectors.google_site.connector",
        class_name="GoogleSitesConnector",
    ),
    DocumentSource.ZENDESK: ConnectorMapping(
        module_path="callosum.connectors.zendesk.connector",
        class_name="ZendeskConnector",
    ),
    DocumentSource.LOOPIO: ConnectorMapping(
        module_path="callosum.connectors.loopio.connector",
        class_name="LoopioConnector",
    ),
    DocumentSource.DROPBOX: ConnectorMapping(
        module_path="callosum.connectors.dropbox.connector",
        class_name="DropboxConnector",
    ),
    DocumentSource.SHAREPOINT: ConnectorMapping(
        module_path="callosum.connectors.sharepoint.connector",
        class_name="SharepointConnector",
    ),
    DocumentSource.TEAMS: ConnectorMapping(
        module_path="callosum.connectors.teams.connector",
        class_name="TeamsConnector",
    ),
    DocumentSource.SALESFORCE: ConnectorMapping(
        module_path="callosum.connectors.salesforce.connector",
        class_name="SalesforceConnector",
    ),
    DocumentSource.DISCOURSE: ConnectorMapping(
        module_path="callosum.connectors.discourse.connector",
        class_name="DiscourseConnector",
    ),
    DocumentSource.AXERO: ConnectorMapping(
        module_path="callosum.connectors.axero.connector",
        class_name="AxeroConnector",
    ),
    DocumentSource.CLICKUP: ConnectorMapping(
        module_path="callosum.connectors.clickup.connector",
        class_name="ClickupConnector",
    ),
    DocumentSource.MEDIAWIKI: ConnectorMapping(
        module_path="callosum.connectors.mediawiki.wiki",
        class_name="MediaWikiConnector",
    ),
    DocumentSource.WIKIPEDIA: ConnectorMapping(
        module_path="callosum.connectors.wikipedia.connector",
        class_name="WikipediaConnector",
    ),
    DocumentSource.ASANA: ConnectorMapping(
        module_path="callosum.connectors.asana.connector",
        class_name="AsanaConnector",
    ),
    DocumentSource.S3: ConnectorMapping(
        module_path="callosum.connectors.blob.connector",
        class_name="BlobStorageConnector",
    ),
    DocumentSource.R2: ConnectorMapping(
        module_path="callosum.connectors.blob.connector",
        class_name="BlobStorageConnector",
    ),
    DocumentSource.GOOGLE_CLOUD_STORAGE: ConnectorMapping(
        module_path="callosum.connectors.blob.connector",
        class_name="BlobStorageConnector",
    ),
    DocumentSource.OCI_STORAGE: ConnectorMapping(
        module_path="callosum.connectors.blob.connector",
        class_name="BlobStorageConnector",
    ),
    DocumentSource.XENFORO: ConnectorMapping(
        module_path="callosum.connectors.xenforo.connector",
        class_name="XenforoConnector",
    ),
    DocumentSource.DISCORD: ConnectorMapping(
        module_path="callosum.connectors.discord.connector",
        class_name="DiscordConnector",
    ),
    DocumentSource.FRESHDESK: ConnectorMapping(
        module_path="callosum.connectors.freshdesk.connector",
        class_name="FreshdeskConnector",
    ),
    DocumentSource.FIREFLIES: ConnectorMapping(
        module_path="callosum.connectors.fireflies.connector",
        class_name="FirefliesConnector",
    ),
    DocumentSource.EGNYTE: ConnectorMapping(
        module_path="callosum.connectors.egnyte.connector",
        class_name="EgnyteConnector",
    ),
    DocumentSource.AIRTABLE: ConnectorMapping(
        module_path="callosum.connectors.airtable.airtable_connector",
        class_name="AirtableConnector",
    ),
    DocumentSource.HIGHSPOT: ConnectorMapping(
        module_path="callosum.connectors.highspot.connector",
        class_name="HighspotConnector",
    ),
    DocumentSource.IMAP: ConnectorMapping(
        module_path="callosum.connectors.imap.connector",
        class_name="ImapConnector",
    ),
    DocumentSource.BITBUCKET: ConnectorMapping(
        module_path="callosum.connectors.bitbucket.connector",
        class_name="BitbucketConnector",
    ),
    DocumentSource.TESTRAIL: ConnectorMapping(
        module_path="callosum.connectors.testrail.connector",
        class_name="TestRailConnector",
    ),
    # just for integration tests
    DocumentSource.MOCK_CONNECTOR: ConnectorMapping(
        module_path="callosum.connectors.mock_connector.connector",
        class_name="MockConnector",
    ),
}
