import generated.callosum_openapi_client.callosum_openapi_client as callosum_api  # type: ignore[import-untyped,unused-ignore]
from tests.integration.common_utils.constants import API_SERVER_URL

api_config = callosum_api.Configuration(host=API_SERVER_URL)
