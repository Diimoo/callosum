from sqlalchemy import distinct
from sqlalchemy.orm import Session

from callosum.configs.constants import DocumentSource
from callosum.db.models import Connector
from callosum.utils.logger import setup_logger

logger = setup_logger()


def fetch_sources_with_connectors(db_session: Session) -> list[DocumentSource]:
    sources = db_session.query(distinct(Connector.source)).all()  # type: ignore

    document_sources = [source[0] for source in sources]

    return document_sources
