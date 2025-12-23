import os
import re
from collections.abc import Iterator
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from typing import IO

from sqlalchemy.orm import Session

from callosum.configs.app_configs import INDEX_BATCH_SIZE
from callosum.configs.constants import DocumentSource
from callosum.connectors.cross_connector_utils.miscellaneous_utils import time_str_to_utc
from callosum.connectors.interfaces import GenerateDocumentsOutput
from callosum.connectors.interfaces import LoadConnector
from callosum.connectors.models import BasicExpertInfo
from callosum.connectors.models import Document
from callosum.connectors.models import Section
from callosum.db.engine import get_session_with_tenant
from callosum.file_processing.extract_file_text import detect_encoding
from callosum.file_processing.extract_file_text import extract_file_text
from callosum.file_processing.extract_file_text import get_file_ext
from callosum.file_processing.extract_file_text import is_text_file_extension
from callosum.file_processing.extract_file_text import is_valid_file_ext
from callosum.file_processing.extract_file_text import load_files_from_zip
from callosum.file_processing.extract_file_text import read_pdf_file
from callosum.file_processing.extract_file_text import read_text_file
from callosum.file_store.file_store import get_default_file_store
from callosum.utils.logger import setup_logger
from shared_configs.configs import POSTGRES_DEFAULT_SCHEMA
from shared_configs.contextvars import CURRENT_TENANT_ID_CONTEXTVAR

logger = setup_logger()


def _read_files_and_metadata(
    file_name: str,
    db_session: Session,
) -> Iterator[tuple[str, IO, dict[str, Any]]]:
    """Reads the file into IO, in the case of a zip file, yields each individual
    file contained within, also includes the metadata dict if packaged in the zip"""
    extension = get_file_ext(file_name)
    metadata: dict[str, Any] = {}
    directory_path = os.path.dirname(file_name)

    file_content = get_default_file_store(db_session).read_file(file_name, mode="b")

    if extension == ".zip":
        for file_info, file, metadata in load_files_from_zip(
            file_content, ignore_dirs=True
        ):
            yield os.path.join(directory_path, file_info.filename), file, metadata
    elif is_valid_file_ext(extension):
        yield file_name, file_content, metadata
    else:
        logger.warning(f"Skipping file '{file_name}' with extension '{extension}'")


CHUNKING_MODE_DEFAULT = "default"
CHUNKING_MODE_LAW = "law"
CHUNKING_MODE_MARKDOWN = "markdown"
CHUNKING_MODE_CODE = "code"
CHUNKING_MODE_AUTO = "auto"

ALLOWED_CHUNKING_MODES = {
    CHUNKING_MODE_DEFAULT,
    CHUNKING_MODE_LAW,
    CHUNKING_MODE_MARKDOWN,
    CHUNKING_MODE_CODE,
    CHUNKING_MODE_AUTO,
}


def _get_chunking_mode_from_metadata(metadata: dict[str, Any] | None) -> str:
    if not metadata:
        return CHUNKING_MODE_DEFAULT
    mode = str(metadata.get("chunking_mode", "")).lower()
    if mode not in ALLOWED_CHUNKING_MODES:
        return CHUNKING_MODE_DEFAULT
    return mode


def _detect_chunking_mode(text: str) -> str:
    """Heuristically detect a suitable chunking mode from the file contents.

    Uses only a prefix of the document to avoid scanning very large files.
    """

    if not text:
        return CHUNKING_MODE_DEFAULT

    sample = text[:20000]
    lower = sample.lower()

    # Law-like signals: paragraphs marked by a7 and typical German law abbreviations
    law_score = sample.count("§") + lower.count(" abs.") + lower.count(" satz") + lower.count(" nr.")

    # Markdown / technical doc signals: markdown and HTML headings
    markdown_headings = re.findall(r"^#{1,3}\s+.+", sample, flags=re.MULTILINE)
    markdown_html_headings = re.findall(r"<h[1-3][^>]*>", sample, flags=re.IGNORECASE)
    md_score = len(markdown_headings) + len(markdown_html_headings)

    # Code-like signals: many semicolons and common language keywords
    code_keywords = ["class ", "def ", "public ", "private ", "protected ", "function "]
    code_score = sample.count(";") + sum(lower.count(kw) for kw in code_keywords)

    scores = {
        CHUNKING_MODE_LAW: law_score,
        CHUNKING_MODE_MARKDOWN: md_score,
        CHUNKING_MODE_CODE: code_score,
    }

    best_mode = max(scores, key=scores.get)
    if scores[best_mode] < 3:
        # Too few signals, fall back to default behavior
        return CHUNKING_MODE_DEFAULT
    return best_mode


def _split_law_into_sections(
    text: str,
    all_metadata: dict[str, Any],
) -> list[Section]:
    """Split legal texts by paragraphs (e.g. "a7 1", "a7 1a").

    Returns an empty list if no clear paragraph structure is detected so that
    callers can fall back to the default behavior.
    """

    # Match paragraph headers including the whole header line
    # Only treat occurrences at the beginning of a line as headers to avoid
    # splitting on inline references such as "nach § 95 ...".
    pattern = re.compile(r"(?m)^\s*§\s*\d+[a-zA-Z]*[^\n]*")
    matches = list(pattern.finditer(text))
    sections: list[Section] = []

    if not matches:
        return []

    base_link = all_metadata.get("link")

    # Everything before the first header becomes a preamble section
    first_start = matches[0].start()
    preamble = text[:first_start].strip()
    if preamble:
        sections.append(Section(link=base_link, text=preamble))

    # Each header + its following body up to the next header becomes a section
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()
        if section_text:
            sections.append(Section(link=base_link, text=section_text))

    return sections


def _split_markdown_into_sections(
    text: str,
    all_metadata: dict[str, Any],
) -> list[Section]:
    """Split technical / markdown docs by headings (#, ##, ###, <h1>-<h3>)."""

    lines = text.splitlines()
    sections: list[Section] = []
    current_lines: list[str] = []
    base_link = all_metadata.get("link")

    def _flush_current() -> None:
        nonlocal current_lines
        if current_lines:
            section_text = "\n".join(current_lines).strip()
            if section_text:
                sections.append(Section(link=base_link, text=section_text))
            current_lines = []

    for line in lines:
        stripped = line.lstrip()
        if re.match(r"^#{1,3}\s+.+", stripped) or re.match(
            r"(?i)^<h[1-3][^>]*>", stripped
        ):
            _flush_current()
            current_lines.append(line)
        else:
            current_lines.append(line)

    _flush_current()

    return sections


def _split_code_into_sections(
    text: str,
    all_metadata: dict[str, Any],
) -> list[Section]:
    """Very simple code splitter.

    For now, split on double newlines to avoid one gigantic section. If this
    does not meaningfully split the file, return an empty list and fall back
    to the default behavior.
    """

    blocks = [block.strip() for block in text.split("\n\n") if block.strip()]
    if len(blocks) < 2:
        return []

    base_link = all_metadata.get("link")
    return [Section(link=base_link, text=block) for block in blocks]


def _build_sections_from_raw_text(
    file_content_raw: str,
    all_metadata: dict[str, Any],
) -> list[Section]:
    """Build document sections from raw file contents based on chunking_mode.

    If a specific mode does not yield any reasonable splits, this falls back
    to the legacy behavior of using a single Section containing the whole
    file contents.
    """

    mode = _get_chunking_mode_from_metadata(all_metadata)
    if mode == CHUNKING_MODE_AUTO:
        mode = _detect_chunking_mode(file_content_raw)

    if mode == CHUNKING_MODE_LAW:
        sections = _split_law_into_sections(file_content_raw, all_metadata)
    elif mode == CHUNKING_MODE_MARKDOWN:
        sections = _split_markdown_into_sections(file_content_raw, all_metadata)
    elif mode == CHUNKING_MODE_CODE:
        sections = _split_code_into_sections(file_content_raw, all_metadata)
    else:
        sections = []

    if not sections:
        return [Section(link=all_metadata.get("link"), text=file_content_raw.strip())]

    return sections


def _process_file(
    file_name: str,
    file: IO[Any],
    metadata: dict[str, Any] | None = None,
    pdf_pass: str | None = None,
) -> list[Document]:
    extension = get_file_ext(file_name)
    if not is_valid_file_ext(extension):
        logger.warning(f"Skipping file '{file_name}' with extension '{extension}'")
        return []

    file_metadata: dict[str, Any] = {}

    if is_text_file_extension(file_name):
        encoding = detect_encoding(file)
        file_content_raw, file_metadata = read_text_file(
            file, encoding=encoding, ignore_callosum_metadata=False
        )

    # Using the PDF reader function directly to pass in password cleanly
    elif extension == ".pdf" and pdf_pass is not None:
        file_content_raw, file_metadata = read_pdf_file(file=file, pdf_pass=pdf_pass)

    else:
        file_content_raw = extract_file_text(
            file=file,
            file_name=file_name,
            break_on_unprocessable=True,
        )

    all_metadata = {**metadata, **file_metadata} if metadata else file_metadata

    # add a prefix to avoid conflicts with other connectors
    doc_id = f"FILE_CONNECTOR__{file_name}"
    if metadata:
        doc_id = metadata.get("document_id") or doc_id

    # If this is set, we will show this in the UI as the "name" of the file
    file_display_name = all_metadata.get("file_display_name") or os.path.basename(
        file_name
    )
    title = (
        all_metadata["title"] or "" if "title" in all_metadata else file_display_name
    )

    time_updated = all_metadata.get("time_updated", datetime.now(timezone.utc))
    if isinstance(time_updated, str):
        time_updated = time_str_to_utc(time_updated)

    dt_str = all_metadata.get("doc_updated_at")
    final_time_updated = time_str_to_utc(dt_str) if dt_str else time_updated

    # Metadata tags separate from the Callosum specific fields
    metadata_tags = {
        k: v
        for k, v in all_metadata.items()
        if k
        not in [
            "document_id",
            "time_updated",
            "doc_updated_at",
            "link",
            "primary_owners",
            "secondary_owners",
            "filename",
            "file_display_name",
            "title",
            "connector_type",
        ]
    }

    source_type_str = all_metadata.get("connector_type")
    source_type = DocumentSource(source_type_str) if source_type_str else None

    p_owner_names = all_metadata.get("primary_owners")
    s_owner_names = all_metadata.get("secondary_owners")
    p_owners = (
        [BasicExpertInfo(display_name=name) for name in p_owner_names]
        if p_owner_names
        else None
    )
    s_owners = (
        [BasicExpertInfo(display_name=name) for name in s_owner_names]
        if s_owner_names
        else None
    )

    sections = _build_sections_from_raw_text(file_content_raw, all_metadata)

    return [
        Document(
            id=doc_id,
            sections=sections,
            source=source_type or DocumentSource.FILE,
            semantic_identifier=file_display_name,
            title=title,
            doc_updated_at=final_time_updated,
            primary_owners=p_owners,
            secondary_owners=s_owners,
            # currently metadata just houses tags, other stuff like owners / updated at have dedicated fields
            metadata=metadata_tags,
        )
    ]


class LocalFileConnector(LoadConnector):
    def __init__(
        self,
        file_locations: list[Path | str],
        tenant_id: str = POSTGRES_DEFAULT_SCHEMA,
        batch_size: int = INDEX_BATCH_SIZE,
        chunking_mode: str | None = None,
    ) -> None:
        self.file_locations = [Path(file_location) for file_location in file_locations]
        self.batch_size = batch_size
        self.tenant_id = tenant_id
        self.pdf_pass: str | None = None
        self.chunking_mode = chunking_mode

    def load_credentials(self, credentials: dict[str, Any]) -> dict[str, Any] | None:
        self.pdf_pass = credentials.get("pdf_password")
        return None

    def load_from_state(self) -> GenerateDocumentsOutput:
        documents: list[Document] = []
        token = CURRENT_TENANT_ID_CONTEXTVAR.set(self.tenant_id)

        with get_session_with_tenant(self.tenant_id) as db_session:
            for file_path in self.file_locations:
                current_datetime = datetime.now(timezone.utc)
                files = _read_files_and_metadata(
                    file_name=str(file_path), db_session=db_session
                )

                for file_name, file, metadata in files:
                    metadata["time_updated"] = metadata.get(
                        "time_updated", current_datetime
                    )
                    # Allow per-connector configuration of chunking behavior while
                    # still permitting per-file overrides via metadata from zips.
                    if self.chunking_mode and "chunking_mode" not in metadata:
                        metadata["chunking_mode"] = self.chunking_mode
                    documents.extend(
                        _process_file(file_name, file, metadata, self.pdf_pass)
                    )

                    if len(documents) >= self.batch_size:
                        yield documents
                        documents = []

            if documents:
                yield documents

        CURRENT_TENANT_ID_CONTEXTVAR.reset(token)


if __name__ == "__main__":
    connector = LocalFileConnector(file_locations=[os.environ["TEST_FILE"]])
    connector.load_credentials({"pdf_password": os.environ["PDF_PASSWORD"]})

    document_batches = connector.load_from_state()
    print(next(document_batches))
