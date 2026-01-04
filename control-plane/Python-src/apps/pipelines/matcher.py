"""
Pipeline trigger matcher for Muelsyse-CI

This module provides logic for matching webhook events against pipeline
trigger configurations to determine if a pipeline should be triggered.
"""
import fnmatch
import logging
import re
from typing import Optional

from apps.webhooks.parsers import PushEvent, PullRequestEvent

logger = logging.getLogger(__name__)


class PipelineMatcher:
    """
    Matches webhook events against pipeline trigger configurations.

    This class implements GitHub Actions-compatible trigger matching logic
    for push and pull_request events.
    """

    def __init__(self, parsed_config: dict):
        """
        Initialize the matcher with a parsed pipeline configuration.

        Args:
            parsed_config: The parsed pipeline configuration dictionary
                          containing the 'on' trigger configuration.
        """
        self.config = parsed_config
        self.triggers = parsed_config.get('on', {})

    def matches_push(self, event: PushEvent) -> bool:
        """
        Check if a push event matches the pipeline's push trigger configuration.

        Args:
            event: The parsed PushEvent.

        Returns:
            True if the event should trigger the pipeline.
        """
        push_config = self.triggers.get('push')

        # If no push trigger is configured, don't match
        if push_config is None:
            return False

        # Empty config means trigger on any push
        if push_config == {} or push_config is True:
            return True

        # Handle tag pushes
        if event.is_tag:
            return self._matches_tag_push(event, push_config)

        # Handle branch pushes
        return self._matches_branch_push(event, push_config)

    def _matches_branch_push(self, event: PushEvent, config: dict) -> bool:
        """Check if a branch push matches the configuration."""
        branch = event.branch

        # Check branches filter
        branches = config.get('branches', [])
        branches_ignore = config.get('branches_ignore', [])

        # If branches-ignore is specified and branch matches, don't trigger
        if branches_ignore and self._matches_pattern_list(branch, branches_ignore):
            logger.debug(f"Branch {branch} matches branches-ignore pattern")
            return False

        # If branches is specified, branch must match
        if branches and not self._matches_pattern_list(branch, branches):
            logger.debug(f"Branch {branch} does not match branches pattern")
            return False

        # Check paths filter
        paths = config.get('paths', [])
        paths_ignore = config.get('paths_ignore', [])

        if paths or paths_ignore:
            changed_files = event.changed_files

            # If paths-ignore is specified and all files match, don't trigger
            if paths_ignore:
                all_ignored = all(
                    self._matches_path_pattern_list(f, paths_ignore)
                    for f in changed_files
                )
                if all_ignored and changed_files:
                    logger.debug("All changed files match paths-ignore pattern")
                    return False

            # If paths is specified, at least one file must match
            if paths:
                any_matches = any(
                    self._matches_path_pattern_list(f, paths)
                    for f in changed_files
                )
                if not any_matches:
                    logger.debug("No changed files match paths pattern")
                    return False

        return True

    def _matches_tag_push(self, event: PushEvent, config: dict) -> bool:
        """Check if a tag push matches the configuration."""
        tag = event.tag
        if not tag:
            return False

        tags = config.get('tags', [])
        tags_ignore = config.get('tags_ignore', [])

        # If tags-ignore is specified and tag matches, don't trigger
        if tags_ignore and self._matches_pattern_list(tag, tags_ignore):
            logger.debug(f"Tag {tag} matches tags-ignore pattern")
            return False

        # If tags is specified, tag must match
        if tags and not self._matches_pattern_list(tag, tags):
            logger.debug(f"Tag {tag} does not match tags pattern")
            return False

        # If no tags filter specified, don't trigger on tags
        # (only trigger on branches by default)
        if not tags:
            return False

        return True

    def matches_pull_request(self, event: PullRequestEvent) -> bool:
        """
        Check if a pull_request event matches the pipeline's trigger configuration.

        Args:
            event: The parsed PullRequestEvent.

        Returns:
            True if the event should trigger the pipeline.
        """
        pr_config = self.triggers.get('pull_request')

        # If no pull_request trigger is configured, don't match
        if pr_config is None:
            return False

        # Empty config means trigger on default actions
        if pr_config == {} or pr_config is True:
            pr_config = {'types': ['opened', 'synchronize', 'reopened']}

        # Check action types
        types = pr_config.get('types', ['opened', 'synchronize', 'reopened'])
        if event.action not in types:
            logger.debug(f"PR action {event.action} not in allowed types: {types}")
            return False

        # Check target branch filter (base branch)
        branches = pr_config.get('branches', [])
        branches_ignore = pr_config.get('branches_ignore', [])

        base_branch = event.base_branch

        # If branches-ignore is specified and branch matches, don't trigger
        if branches_ignore and self._matches_pattern_list(base_branch, branches_ignore):
            logger.debug(f"Base branch {base_branch} matches branches-ignore pattern")
            return False

        # If branches is specified, branch must match
        if branches and not self._matches_pattern_list(base_branch, branches):
            logger.debug(f"Base branch {base_branch} does not match branches pattern")
            return False

        # Note: paths filtering for PRs would require API call to get changed files
        # This is left as a TODO for now

        return True

    def _matches_pattern_list(self, value: str, patterns: list) -> bool:
        """
        Check if a value matches any pattern in the list.

        Supports glob patterns with *, **, and ? wildcards.
        """
        for pattern in patterns:
            if self._matches_pattern(value, pattern):
                return True
        return False

    def _matches_pattern(self, value: str, pattern: str) -> bool:
        """
        Check if a value matches a single pattern.

        Supports:
        - Exact match
        - Glob patterns: *, **, ?
        - Feature branch patterns like feature/* or release/**
        """
        # Exact match
        if value == pattern:
            return True

        # Convert GitHub Actions style pattern to fnmatch pattern
        # ** matches any character including /
        # * matches any character except /

        # First, handle ** by replacing with a special marker
        regex_pattern = pattern

        # Escape special regex characters except * and ?
        regex_pattern = re.escape(regex_pattern)

        # Restore * and ? and convert to regex
        # \*\* -> .*
        regex_pattern = regex_pattern.replace(r'\*\*', '.*')
        # \* -> [^/]*
        regex_pattern = regex_pattern.replace(r'\*', '[^/]*')
        # \? -> .
        regex_pattern = regex_pattern.replace(r'\?', '.')

        # Anchor the pattern
        regex_pattern = f'^{regex_pattern}$'

        try:
            return bool(re.match(regex_pattern, value))
        except re.error:
            logger.warning(f"Invalid pattern: {pattern}")
            return False

    def _matches_path_pattern_list(self, path: str, patterns: list) -> bool:
        """
        Check if a file path matches any pattern in the list.

        Supports glob patterns for file paths.
        """
        for pattern in patterns:
            if self._matches_path_pattern(path, pattern):
                return True
        return False

    def _matches_path_pattern(self, path: str, pattern: str) -> bool:
        """
        Check if a file path matches a pattern.

        Supports:
        - ** for any directory depth
        - * for any filename
        - Exact directory/file matching
        """
        # Use fnmatch for simple patterns
        if fnmatch.fnmatch(path, pattern):
            return True

        # Handle ** pattern for any directory depth
        if '**' in pattern:
            # Convert ** to regex
            regex_pattern = pattern.replace('.', r'\.')
            regex_pattern = regex_pattern.replace('**', '.*')
            regex_pattern = regex_pattern.replace('*', '[^/]*')
            regex_pattern = f'^{regex_pattern}$'

            try:
                return bool(re.match(regex_pattern, path))
            except re.error:
                pass

        return False

    def get_trigger_types(self) -> list:
        """Get list of configured trigger types."""
        return list(self.triggers.keys())


def matches_pipeline_triggers(
    parsed_config: dict,
    event_type: str,
    event
) -> bool:
    """
    Convenience function to check if an event matches pipeline triggers.

    Args:
        parsed_config: The parsed pipeline configuration.
        event_type: The event type ('push' or 'pull_request').
        event: The parsed event object.

    Returns:
        True if the event should trigger the pipeline.
    """
    matcher = PipelineMatcher(parsed_config)

    if event_type == 'push' and isinstance(event, PushEvent):
        return matcher.matches_push(event)
    elif event_type == 'pull_request' and isinstance(event, PullRequestEvent):
        return matcher.matches_pull_request(event)

    return False
