#!/usr/bin/env python3
"""
RAG Enterprise Test Suite Runner

Runs all enterprise-grade RAG tests with a single command:
    python -m pytest tests/rag_enterprise_tests.py -v

Or run specific test categories:
    python -m pytest tests/rag_enterprise_tests.py -v -k "security"
    python -m pytest tests/rag_enterprise_tests.py -v -k "resilience"
    python -m pytest tests/rag_enterprise_tests.py -v -k "cache"
    python -m pytest tests/rag_enterprise_tests.py -v -k "multitenant"
"""

import subprocess
import sys
from pathlib import Path


# Test modules to run
TEST_MODULES = [
    # Security tests
    "tests/unit/security/test_rag_security.py",
    # Resilience tests  
    "tests/unit/utils/test_resilience.py",
    # Semantic cache tests
    "tests/unit/context/test_semantic_cache.py",
    # Multi-tenant isolation tests
    "tests/unit/test_multitenant_isolation.py",
]


def run_tests(verbose: bool = True, coverage: bool = False) -> int:
    """Run all RAG enterprise tests."""
    backend_dir = Path(__file__).parent.parent
    
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=onyx", "--cov-report=term-missing"])
    
    cmd.extend(TEST_MODULES)
    
    print(f"Running: {' '.join(cmd)}")
    print(f"Working directory: {backend_dir}")
    print("-" * 60)
    
    result = subprocess.run(cmd, cwd=backend_dir)
    return result.returncode


if __name__ == "__main__":
    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    coverage = "--cov" in sys.argv
    
    exit_code = run_tests(verbose=verbose, coverage=coverage)
    sys.exit(exit_code)
