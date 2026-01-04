"""
GitHub Webhook event parsers for Muelsyse-CI

This module provides parsers for extracting relevant information from
GitHub webhook payloads for different event types.
"""
import logging
from dataclasses import dataclass, field
from typing import Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class GitHubRepository:
    """Parsed GitHub repository information."""
    id: int = 0
    name: str = ""
    full_name: str = ""
    clone_url: str = ""
    ssh_url: str = ""
    html_url: str = ""
    default_branch: str = "main"
    private: bool = False

    @classmethod
    def from_payload(cls, data: dict) -> 'GitHubRepository':
        """Create a GitHubRepository from a payload dictionary."""
        if not data:
            return cls()
        return cls(
            id=data.get('id', 0),
            name=data.get('name', ''),
            full_name=data.get('full_name', ''),
            clone_url=data.get('clone_url', ''),
            ssh_url=data.get('ssh_url', ''),
            html_url=data.get('html_url', ''),
            default_branch=data.get('default_branch', 'main'),
            private=data.get('private', False),
        )


@dataclass
class GitHubUser:
    """Parsed GitHub user information."""
    id: int = 0
    login: str = ""
    avatar_url: str = ""
    html_url: str = ""

    @classmethod
    def from_payload(cls, data: dict) -> 'GitHubUser':
        """Create a GitHubUser from a payload dictionary."""
        if not data:
            return cls()
        return cls(
            id=data.get('id', 0),
            login=data.get('login', ''),
            avatar_url=data.get('avatar_url', ''),
            html_url=data.get('html_url', ''),
        )


@dataclass
class GitHubCommit:
    """Parsed GitHub commit information."""
    id: str = ""
    message: str = ""
    timestamp: str = ""
    author_name: str = ""
    author_email: str = ""
    url: str = ""
    added: list = field(default_factory=list)
    removed: list = field(default_factory=list)
    modified: list = field(default_factory=list)

    @classmethod
    def from_payload(cls, data: dict) -> 'GitHubCommit':
        """Create a GitHubCommit from a payload dictionary."""
        if not data:
            return cls()
        author = data.get('author', {})
        return cls(
            id=data.get('id', ''),
            message=data.get('message', ''),
            timestamp=data.get('timestamp', ''),
            author_name=author.get('name', ''),
            author_email=author.get('email', ''),
            url=data.get('url', ''),
            added=data.get('added', []),
            removed=data.get('removed', []),
            modified=data.get('modified', []),
        )


@dataclass
class PushEvent:
    """Parsed GitHub push event."""
    ref: str = ""
    before: str = ""
    after: str = ""
    created: bool = False
    deleted: bool = False
    forced: bool = False
    base_ref: Optional[str] = None
    compare_url: str = ""
    commits: list = field(default_factory=list)
    head_commit: Optional[GitHubCommit] = None
    repository: Optional[GitHubRepository] = None
    sender: Optional[GitHubUser] = None

    @property
    def branch(self) -> str:
        """Extract branch name from ref."""
        if self.ref.startswith('refs/heads/'):
            return self.ref[len('refs/heads/'):]
        return self.ref

    @property
    def tag(self) -> Optional[str]:
        """Extract tag name from ref if this is a tag push."""
        if self.ref.startswith('refs/tags/'):
            return self.ref[len('refs/tags/'):]
        return None

    @property
    def is_tag(self) -> bool:
        """Check if this push is for a tag."""
        return self.ref.startswith('refs/tags/')

    @property
    def is_branch(self) -> bool:
        """Check if this push is for a branch."""
        return self.ref.startswith('refs/heads/')

    @property
    def commit_sha(self) -> str:
        """Get the head commit SHA."""
        return self.after

    @property
    def changed_files(self) -> list:
        """Get list of all changed files in the push."""
        files = set()
        for commit in self.commits:
            if isinstance(commit, GitHubCommit):
                files.update(commit.added)
                files.update(commit.removed)
                files.update(commit.modified)
            elif isinstance(commit, dict):
                files.update(commit.get('added', []))
                files.update(commit.get('removed', []))
                files.update(commit.get('modified', []))
        return list(files)


@dataclass
class PullRequestEvent:
    """Parsed GitHub pull_request event."""
    action: str = ""
    number: int = 0
    pull_request: dict = field(default_factory=dict)
    repository: Optional[GitHubRepository] = None
    sender: Optional[GitHubUser] = None

    @property
    def title(self) -> str:
        """Get PR title."""
        return self.pull_request.get('title', '')

    @property
    def body(self) -> str:
        """Get PR body/description."""
        return self.pull_request.get('body', '') or ''

    @property
    def state(self) -> str:
        """Get PR state (open, closed)."""
        return self.pull_request.get('state', '')

    @property
    def merged(self) -> bool:
        """Check if PR is merged."""
        return self.pull_request.get('merged', False)

    @property
    def head_sha(self) -> str:
        """Get the head commit SHA."""
        head = self.pull_request.get('head', {})
        return head.get('sha', '')

    @property
    def head_branch(self) -> str:
        """Get the head branch name."""
        head = self.pull_request.get('head', {})
        return head.get('ref', '')

    @property
    def base_branch(self) -> str:
        """Get the base branch name."""
        base = self.pull_request.get('base', {})
        return base.get('ref', '')

    @property
    def head_repo(self) -> str:
        """Get the head repository full name."""
        head = self.pull_request.get('head', {})
        repo = head.get('repo', {})
        return repo.get('full_name', '')

    @property
    def base_repo(self) -> str:
        """Get the base repository full name."""
        base = self.pull_request.get('base', {})
        repo = base.get('repo', {})
        return repo.get('full_name', '')

    @property
    def is_fork(self) -> bool:
        """Check if PR is from a fork."""
        return self.head_repo != self.base_repo

    @property
    def changed_files(self) -> list:
        """Get list of changed files (if available in payload)."""
        return []  # Note: PR payloads don't include file list, need API call


class GitHubEventParser:
    """
    Parser for GitHub webhook events.

    Supports parsing push and pull_request events into structured objects.
    """

    SUPPORTED_EVENTS = ['push', 'pull_request', 'ping']

    def __init__(self, event_type: str, payload: dict):
        """
        Initialize the parser.

        Args:
            event_type: The GitHub event type (e.g., 'push', 'pull_request').
            payload: The webhook payload dictionary.
        """
        self.event_type = event_type
        self.payload = payload

    def parse(self) -> Any:
        """
        Parse the webhook payload based on event type.

        Returns:
            A parsed event object (PushEvent, PullRequestEvent, etc.) or None.

        Raises:
            ValueError: If the event type is not supported.
        """
        if self.event_type == 'push':
            return self._parse_push()
        elif self.event_type == 'pull_request':
            return self._parse_pull_request()
        elif self.event_type == 'ping':
            return self._parse_ping()
        else:
            logger.warning(f"Unsupported event type: {self.event_type}")
            return None

    def _parse_push(self) -> PushEvent:
        """Parse a push event payload."""
        commits = [
            GitHubCommit.from_payload(c)
            for c in self.payload.get('commits', [])
        ]

        head_commit_data = self.payload.get('head_commit')
        head_commit = GitHubCommit.from_payload(head_commit_data) if head_commit_data else None

        return PushEvent(
            ref=self.payload.get('ref', ''),
            before=self.payload.get('before', ''),
            after=self.payload.get('after', ''),
            created=self.payload.get('created', False),
            deleted=self.payload.get('deleted', False),
            forced=self.payload.get('forced', False),
            base_ref=self.payload.get('base_ref'),
            compare_url=self.payload.get('compare', ''),
            commits=commits,
            head_commit=head_commit,
            repository=GitHubRepository.from_payload(self.payload.get('repository', {})),
            sender=GitHubUser.from_payload(self.payload.get('sender', {})),
        )

    def _parse_pull_request(self) -> PullRequestEvent:
        """Parse a pull_request event payload."""
        return PullRequestEvent(
            action=self.payload.get('action', ''),
            number=self.payload.get('number', 0),
            pull_request=self.payload.get('pull_request', {}),
            repository=GitHubRepository.from_payload(self.payload.get('repository', {})),
            sender=GitHubUser.from_payload(self.payload.get('sender', {})),
        )

    def _parse_ping(self) -> dict:
        """Parse a ping event payload."""
        return {
            'zen': self.payload.get('zen', ''),
            'hook_id': self.payload.get('hook_id'),
            'hook': self.payload.get('hook', {}),
        }


def parse_github_event(event_type: str, payload: dict) -> Any:
    """
    Convenience function to parse a GitHub webhook event.

    Args:
        event_type: The GitHub event type (e.g., 'push', 'pull_request').
        payload: The webhook payload dictionary.

    Returns:
        A parsed event object or None if not supported.
    """
    parser = GitHubEventParser(event_type, payload)
    return parser.parse()
