import pytest

from callosum.auth.email_utils import build_user_email_invite
from callosum.auth.email_utils import send_email
from callosum.configs.constants import AuthType
from callosum.configs.constants import CALLOSUM_DEFAULT_APPLICATION_NAME
from callosum.db.engine.sql_engine import SqlEngine
from callosum.server.runtime.callosum_runtime import CallosumRuntime


@pytest.mark.skip(
    reason="This sends real emails, so only run when you really want to test this!"
)
def test_send_user_email_invite() -> None:
    SqlEngine.init_engine(pool_size=20, max_overflow=5)

    application_name = CALLOSUM_DEFAULT_APPLICATION_NAME

    callosum_file = CallosumRuntime.get_emailable_logo()

    subject = f"Invitation to Join {application_name} Organization"

    FROM_EMAIL = "noreply@callosum.app"
    TO_EMAIL = "support@callosum.app"
    text_content, html_content = build_user_email_invite(
        FROM_EMAIL, TO_EMAIL, CALLOSUM_DEFAULT_APPLICATION_NAME, AuthType.CLOUD
    )

    send_email(
        TO_EMAIL,
        subject,
        html_content,
        text_content,
        mail_from=FROM_EMAIL,
        inline_png=("logo.png", callosum_file.data),
    )
