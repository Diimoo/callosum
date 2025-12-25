import os

__version__ = os.environ.get("CALLOSUM_VERSION", "") or "Development"
