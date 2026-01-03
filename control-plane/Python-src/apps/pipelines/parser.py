"""
Pipeline YAML parser for Muelsyse-CI

This module implements a GitHub Actions compatible YAML parser.
"""
import re
from typing import Any
import yaml
from dataclasses import dataclass, field

from apps.core.exceptions import PipelineValidationError


@dataclass
class TriggerConfig:
    """Parsed trigger configuration."""
    push: dict = field(default_factory=dict)
    pull_request: dict = field(default_factory=dict)
    schedule: list = field(default_factory=list)
    workflow_dispatch: dict = field(default_factory=dict)
    webhook: dict = field(default_factory=dict)


@dataclass
class StepConfig:
    """Parsed step configuration."""
    name: str = ""
    id: str = ""
    run: str = ""
    uses: str = ""
    with_inputs: dict = field(default_factory=dict)
    env: dict = field(default_factory=dict)
    working_directory: str = ""
    shell: str = "bash"
    condition: str = ""
    continue_on_error: bool = False
    timeout_minutes: int = 60


@dataclass
class JobConfig:
    """Parsed job configuration."""
    name: str = ""
    runs_on: list = field(default_factory=list)
    needs: list = field(default_factory=list)
    condition: str = ""
    container: dict = field(default_factory=dict)
    services: dict = field(default_factory=dict)
    env: dict = field(default_factory=dict)
    steps: list = field(default_factory=list)
    strategy: dict = field(default_factory=dict)
    timeout_minutes: int = 60
    outputs: dict = field(default_factory=dict)


@dataclass
class PipelineConfigParsed:
    """Parsed pipeline configuration."""
    name: str = ""
    on: TriggerConfig = field(default_factory=TriggerConfig)
    env: dict = field(default_factory=dict)
    defaults: dict = field(default_factory=dict)
    concurrency: dict = field(default_factory=dict)
    jobs: dict = field(default_factory=dict)


class PipelineParser:
    """
    Parser for GitHub Actions style pipeline YAML configurations.
    """

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def parse(self, yaml_content: str) -> tuple[dict, list[str]]:
        """
        Parse YAML content and return parsed configuration.

        Returns:
            tuple: (parsed_config dict, list of validation errors)
        """
        self.errors = []
        self.warnings = []

        try:
            raw_config = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            return {}, [f"YAML syntax error: {e}"]

        if not isinstance(raw_config, dict):
            return {}, ["Pipeline configuration must be a YAML object"]

        parsed = self._parse_config(raw_config)

        return parsed, self.errors

    def _parse_config(self, raw: dict) -> dict:
        """Parse the raw configuration dictionary."""
        config = {
            'name': raw.get('name', 'Unnamed Pipeline'),
            'on': self._parse_triggers(raw.get('on', {})),
            'env': raw.get('env', {}),
            'defaults': raw.get('defaults', {}),
            'concurrency': self._parse_concurrency(raw.get('concurrency', {})),
            'jobs': self._parse_jobs(raw.get('jobs', {})),
        }

        # Validation
        if not config['jobs']:
            self.errors.append("Pipeline must have at least one job")

        return config

    def _parse_triggers(self, on_config) -> dict:
        """Parse trigger configuration."""
        if isinstance(on_config, str):
            # Simple trigger: on: push
            return {on_config: {}}

        if isinstance(on_config, list):
            # List of triggers: on: [push, pull_request]
            return {trigger: {} for trigger in on_config}

        if isinstance(on_config, dict):
            triggers = {}

            # Push trigger
            if 'push' in on_config:
                triggers['push'] = self._parse_push_trigger(on_config['push'])

            # Pull request trigger
            if 'pull_request' in on_config:
                triggers['pull_request'] = self._parse_pr_trigger(on_config['pull_request'])

            # Schedule trigger
            if 'schedule' in on_config:
                triggers['schedule'] = self._parse_schedule_trigger(on_config['schedule'])

            # Workflow dispatch (manual trigger)
            if 'workflow_dispatch' in on_config:
                triggers['workflow_dispatch'] = self._parse_workflow_dispatch(
                    on_config['workflow_dispatch']
                )

            return triggers

        return {}

    def _parse_push_trigger(self, config) -> dict:
        """Parse push trigger configuration."""
        if config is None:
            return {}

        return {
            'branches': config.get('branches', []),
            'branches_ignore': config.get('branches-ignore', []),
            'paths': config.get('paths', []),
            'paths_ignore': config.get('paths-ignore', []),
            'tags': config.get('tags', []),
            'tags_ignore': config.get('tags-ignore', []),
        }

    def _parse_pr_trigger(self, config) -> dict:
        """Parse pull_request trigger configuration."""
        if config is None:
            return {}

        return {
            'branches': config.get('branches', []),
            'branches_ignore': config.get('branches-ignore', []),
            'paths': config.get('paths', []),
            'paths_ignore': config.get('paths-ignore', []),
            'types': config.get('types', ['opened', 'synchronize', 'reopened']),
        }

    def _parse_schedule_trigger(self, config: list) -> list:
        """Parse schedule trigger configuration."""
        schedules = []
        for item in config:
            if isinstance(item, dict) and 'cron' in item:
                # Validate cron expression
                cron = item['cron']
                if self._validate_cron(cron):
                    schedules.append({'cron': cron})
                else:
                    self.errors.append(f"Invalid cron expression: {cron}")
        return schedules

    def _parse_workflow_dispatch(self, config) -> dict:
        """Parse workflow_dispatch trigger configuration."""
        if config is None:
            return {'inputs': {}}

        inputs = {}
        for name, input_config in config.get('inputs', {}).items():
            inputs[name] = {
                'description': input_config.get('description', ''),
                'required': input_config.get('required', False),
                'default': input_config.get('default'),
                'type': input_config.get('type', 'string'),
                'options': input_config.get('options', []),
            }

        return {'inputs': inputs}

    def _parse_concurrency(self, config) -> dict:
        """Parse concurrency configuration."""
        if isinstance(config, str):
            return {'group': config, 'cancel_in_progress': False}

        if isinstance(config, dict):
            return {
                'group': config.get('group', ''),
                'cancel_in_progress': config.get('cancel-in-progress', False),
            }

        return {}

    def _parse_jobs(self, jobs_config: dict) -> dict:
        """Parse all jobs."""
        jobs = {}

        if not jobs_config:
            return jobs

        for job_key, job_config in jobs_config.items():
            if not self._validate_job_key(job_key):
                self.errors.append(f"Invalid job key: {job_key}")
                continue

            jobs[job_key] = self._parse_job(job_key, job_config)

        # Validate job dependencies
        self._validate_job_dependencies(jobs)

        return jobs

    def _parse_job(self, job_key: str, config: dict) -> dict:
        """Parse a single job configuration."""
        job = {
            'name': config.get('name', job_key),
            'runs_on': self._normalize_runs_on(config.get('runs-on', [])),
            'needs': self._normalize_list(config.get('needs', [])),
            'condition': config.get('if', ''),
            'container': self._parse_container(config.get('container')),
            'services': self._parse_services(config.get('services', {})),
            'env': config.get('env', {}),
            'steps': self._parse_steps(config.get('steps', [])),
            'strategy': self._parse_strategy(config.get('strategy', {})),
            'timeout_minutes': config.get('timeout-minutes', 60),
            'outputs': config.get('outputs', {}),
        }

        if not job['runs_on']:
            self.errors.append(f"Job '{job_key}' must specify 'runs-on'")

        if not job['steps']:
            self.errors.append(f"Job '{job_key}' must have at least one step")

        return job

    def _parse_container(self, config) -> dict:
        """Parse container configuration."""
        if config is None:
            return {}

        if isinstance(config, str):
            return {'image': config}

        return {
            'image': config.get('image', ''),
            'credentials': config.get('credentials', {}),
            'env': config.get('env', {}),
            'ports': config.get('ports', []),
            'volumes': config.get('volumes', []),
            'options': config.get('options', ''),
        }

    def _parse_services(self, services_config: dict) -> dict:
        """Parse service containers configuration."""
        services = {}

        for name, config in services_config.items():
            services[name] = {
                'image': config.get('image', ''),
                'credentials': config.get('credentials', {}),
                'env': config.get('env', {}),
                'ports': config.get('ports', []),
                'volumes': config.get('volumes', []),
                'options': config.get('options', ''),
            }

        return services

    def _parse_strategy(self, config: dict) -> dict:
        """Parse job strategy (matrix)."""
        if not config:
            return {}

        strategy = {
            'fail_fast': config.get('fail-fast', True),
            'max_parallel': config.get('max-parallel'),
            'matrix': {},
        }

        matrix = config.get('matrix', {})
        if matrix:
            strategy['matrix'] = {
                'include': matrix.get('include', []),
                'exclude': matrix.get('exclude', []),
                'variables': {
                    k: v for k, v in matrix.items()
                    if k not in ('include', 'exclude')
                },
            }

        return strategy

    def _parse_steps(self, steps_config: list) -> list:
        """Parse job steps."""
        steps = []

        for i, step_config in enumerate(steps_config):
            step = self._parse_step(i, step_config)
            if step:
                steps.append(step)

        return steps

    def _parse_step(self, index: int, config: dict) -> dict:
        """Parse a single step."""
        step = {
            'name': config.get('name', f'Step {index + 1}'),
            'id': config.get('id', ''),
            'run': config.get('run', ''),
            'uses': config.get('uses', ''),
            'with': config.get('with', {}),
            'env': config.get('env', {}),
            'working_directory': config.get('working-directory', ''),
            'shell': config.get('shell', 'bash'),
            'condition': config.get('if', ''),
            'continue_on_error': config.get('continue-on-error', False),
            'timeout_minutes': config.get('timeout-minutes', 60),
        }

        # Validate: must have either 'run' or 'uses'
        if not step['run'] and not step['uses']:
            self.errors.append(
                f"Step {index + 1} must have either 'run' or 'uses'"
            )

        if step['run'] and step['uses']:
            self.errors.append(
                f"Step {index + 1} cannot have both 'run' and 'uses'"
            )

        # Determine step type
        step['type'] = 'uses' if step['uses'] else 'run'

        return step

    def _normalize_runs_on(self, runs_on) -> list:
        """Normalize runs-on to a list."""
        if isinstance(runs_on, str):
            return [runs_on]
        if isinstance(runs_on, list):
            return runs_on
        return []

    def _normalize_list(self, value) -> list:
        """Normalize a value to a list."""
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return value
        return []

    def _validate_job_key(self, key: str) -> bool:
        """Validate job key format."""
        # Job keys must start with a letter or underscore
        # and contain only alphanumeric characters, underscores, or hyphens
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_-]*$'
        return bool(re.match(pattern, key))

    def _validate_job_dependencies(self, jobs: dict) -> None:
        """Validate that all job dependencies exist."""
        job_keys = set(jobs.keys())

        for job_key, job in jobs.items():
            for needed_job in job['needs']:
                if needed_job not in job_keys:
                    self.errors.append(
                        f"Job '{job_key}' depends on non-existent job '{needed_job}'"
                    )

        # Check for circular dependencies
        self._check_circular_dependencies(jobs)

    def _check_circular_dependencies(self, jobs: dict) -> None:
        """Check for circular dependencies in job graph."""
        visited = set()
        rec_stack = set()

        def has_cycle(job_key: str) -> bool:
            visited.add(job_key)
            rec_stack.add(job_key)

            for dep in jobs.get(job_key, {}).get('needs', []):
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True

            rec_stack.remove(job_key)
            return False

        for job_key in jobs:
            if job_key not in visited:
                if has_cycle(job_key):
                    self.errors.append("Circular dependency detected in job graph")
                    return

    def _validate_cron(self, expression: str) -> bool:
        """Validate cron expression format."""
        # Basic validation: 5 or 6 fields
        parts = expression.split()
        if len(parts) not in (5, 6):
            return False
        return True


def parse_pipeline_yaml(yaml_content: str) -> tuple[dict, list[str]]:
    """
    Convenience function to parse pipeline YAML.

    Args:
        yaml_content: Raw YAML content

    Returns:
        tuple: (parsed_config, errors)
    """
    parser = PipelineParser()
    return parser.parse(yaml_content)
