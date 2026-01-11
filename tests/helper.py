"""
Test helper utilities for running test files directly.

Usage:
    from helper import bootstrap, select_and_run
    bootstrap()
    if __name__ == "__main__":
        import sys
        select_and_run(__file__, sys.argv[1:])

Selectors:
    all, isolation, skipped, service, entities, operations, integration, or pattern
"""

import os
import sys
import pytest


def bootstrap():
    """Ensure project root is on sys.path so 'app' and 'main' import work.
    Returns the project root path.
    """
    current_dir = os.path.dirname(__file__)
    root_dir = os.path.abspath(os.path.join(current_dir, ".."))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    return root_dir


def select_and_run(test_file: str, args=None):
    """Run pytest for a specific test file with optional selectors or flags.

    - If args contain pytest flags (start with '-'), pass through.
    - Otherwise, support preset selectors or treat arg as a pattern for -k.
    """
    args = list(args) if args else []

    # Pass through pytest flags like -v, -k, -q, etc.
    if any(a.startswith("-") for a in args):
        return pytest.main([test_file] + args)

    # Default: run all active tests verbosely
    if not args:
        return pytest.main([test_file, "-v"])

    arg = args[0]
    if arg == "all":
        return pytest.main([test_file, "-v", "-rs"])  # include skipped reason
    if arg == "isolation":
        return pytest.main([test_file, "-v", "-m", "not skip"])  # exclude @skip
    if arg == "skipped":
        return pytest.main([test_file, "-v", "-rs", "-k",
                            "discover_schemas or discover_specific or discover_nonexistent or full_discovery or schema_example or multiple_entity"])  # only skipped names
    if arg == "service":
        return pytest.main([test_file, "-v", "-k", "test_get_service"])
    if arg == "entities":
        return pytest.main([test_file, "-v", "-k", "discover_entity_types"])
    if arg == "operations":
        return pytest.main([test_file, "-v", "-k", "test_discover_operations"])
    if arg == "integration":
        return pytest.main([test_file, "-v", "-k", "flow or accuracy or multiple"])  # integration-oriented names

    # Treat as a custom pattern
    return pytest.main([test_file, "-v", "-k", arg])
