from slack_sdk import WebClient
from sqlalchemy.orm import Session

from callosum.db.models import Prompt
from callosum.db.models import SlackChannelConfig
from callosum.callosumbot.slack.models import SlackMessageInfo
from callosum.utils.logger import CallosumLoggingAdapter
from callosum.utils.logger import setup_logger
from callosum.utils.variable_functionality import fetch_versioned_implementation

logger = setup_logger()


def handle_standard_answers(
    message_info: SlackMessageInfo,
    receiver_ids: list[str] | None,
    slack_channel_config: SlackChannelConfig | None,
    prompt: Prompt | None,
    logger: CallosumLoggingAdapter,
    client: WebClient,
    db_session: Session,
) -> bool:
    """Returns whether one or more Standard Answer message blocks were
    emitted by the Slack bot"""
    versioned_handle_standard_answers = fetch_versioned_implementation(
        "callosum.callosumbot.slack.handlers.handle_standard_answers",
        "_handle_standard_answers",
    )
    return versioned_handle_standard_answers(
        message_info=message_info,
        receiver_ids=receiver_ids,
        slack_channel_config=slack_channel_config,
        prompt=prompt,
        logger=logger,
        client=client,
        db_session=db_session,
    )


def _handle_standard_answers(
    message_info: SlackMessageInfo,
    receiver_ids: list[str] | None,
    slack_channel_config: SlackChannelConfig | None,
    prompt: Prompt | None,
    logger: CallosumLoggingAdapter,
    client: WebClient,
    db_session: Session,
) -> bool:
    """
    Standard Answers are a paid Enterprise Edition feature. This is the fallback
    function handling the case where EE features are not enabled.

    Always returns false i.e. since EE features are not enabled, we NEVER create any
    Slack message blocks.
    """
    return False
