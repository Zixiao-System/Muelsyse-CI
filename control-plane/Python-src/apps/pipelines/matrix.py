"""
Matrix expansion utilities for Muelsyse-CI

This module handles expanding job matrices into individual job instances.
"""
import itertools
from typing import Any, Generator
from copy import deepcopy


def expand_matrix(strategy: dict) -> Generator[dict, None, None]:
    """
    Expand a job strategy matrix into individual combinations.

    Args:
        strategy: Job strategy configuration containing matrix

    Yields:
        dict: Matrix variable values for each combination

    Example:
        strategy = {
            'matrix': {
                'variables': {
                    'os': ['ubuntu-22.04', 'macos-latest'],
                    'node': ['18', '20']
                },
                'include': [{'os': 'ubuntu-22.04', 'node': '16', 'experimental': True}],
                'exclude': [{'os': 'macos-latest', 'node': '18'}]
            }
        }

        # Yields:
        # {'os': 'ubuntu-22.04', 'node': '18'}
        # {'os': 'ubuntu-22.04', 'node': '20'}
        # {'os': 'macos-latest', 'node': '20'}  # '18' excluded
        # {'os': 'ubuntu-22.04', 'node': '16', 'experimental': True}  # from include
    """
    matrix = strategy.get('matrix', {})

    if not matrix:
        yield {}
        return

    variables = matrix.get('variables', {})
    include = matrix.get('include', [])
    exclude = matrix.get('exclude', [])

    # Generate all combinations
    if variables:
        keys = list(variables.keys())
        values = [variables[k] for k in keys]

        for combo in itertools.product(*values):
            combination = dict(zip(keys, combo))

            # Check if this combination should be excluded
            if not _should_exclude(combination, exclude):
                yield combination

    # Add included configurations
    for included in include:
        yield deepcopy(included)


def _should_exclude(combination: dict, exclude_list: list) -> bool:
    """
    Check if a combination matches any exclude pattern.

    A combination is excluded if all keys in the exclude pattern
    match the corresponding values in the combination.
    """
    for exclude_pattern in exclude_list:
        if _matches_pattern(combination, exclude_pattern):
            return True
    return False


def _matches_pattern(combination: dict, pattern: dict) -> bool:
    """
    Check if a combination matches a pattern.

    All keys in the pattern must exist in the combination
    with matching values.
    """
    for key, value in pattern.items():
        if key not in combination or combination[key] != value:
            return False
    return True


def count_matrix_combinations(strategy: dict) -> int:
    """
    Count the total number of matrix combinations.

    Args:
        strategy: Job strategy configuration

    Returns:
        Number of combinations
    """
    return sum(1 for _ in expand_matrix(strategy))


def get_matrix_display_name(job_name: str, matrix_values: dict) -> str:
    """
    Generate a display name for a matrix job instance.

    Args:
        job_name: Base job name
        matrix_values: Matrix variable values

    Returns:
        Display name like "Build (ubuntu-22.04, node-18)"
    """
    if not matrix_values:
        return job_name

    # Format values for display
    values_str = ", ".join(
        f"{v}" if isinstance(v, (str, int, float)) else str(v)
        for v in matrix_values.values()
    )

    return f"{job_name} ({values_str})"
