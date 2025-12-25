from callosum.evals.models import EvalProvider
from callosum.evals.providers.braintrust import BraintrustEvalProvider


def get_default_provider() -> EvalProvider:
    return BraintrustEvalProvider()
