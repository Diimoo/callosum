from callosum.chat.chat_utils import combine_message_chain
from callosum.configs.chat_configs import LANGUAGE_CHAT_NAMING_HINT
from callosum.db.models import ChatMessage
from callosum.db.search_settings import get_multilingual_expansion
from callosum.llm.interfaces import LLM
from callosum.llm.utils import llm_response_to_string
from callosum.prompts.chat_prompts import CHAT_NAMING
from callosum.utils.logger import setup_logger

logger = setup_logger()


def get_renamed_conversation_name(
    full_history: list[ChatMessage],
    llm: LLM,
) -> str:
    max_context_for_naming = 1000
    history_str = combine_message_chain(
        messages=full_history, token_limit=max_context_for_naming
    )

    language_hint = (
        f"\n{LANGUAGE_CHAT_NAMING_HINT.strip()}"
        if bool(get_multilingual_expansion())
        else ""
    )

    prompt = CHAT_NAMING.format(
        language_hint_or_empty=language_hint, chat_history=history_str
    )

    new_name_raw = llm_response_to_string(llm.invoke(prompt))

    new_name = new_name_raw.strip().strip('"')

    logger.debug(f"New Session Name: {new_name}")

    return new_name
