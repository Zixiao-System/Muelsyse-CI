"""
Pipeline YAML schema validation using JSON Schema.
"""
import json
from jsonschema import Draft7Validator, ValidationError

# JSON Schema for pipeline configuration
PIPELINE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "name": {"type": "string", "maxLength": 200},
        "on": {
            "oneOf": [
                {"type": "string"},
                {"type": "array", "items": {"type": "string"}},
                {
                    "type": "object",
                    "properties": {
                        "push": {"$ref": "#/definitions/pushTrigger"},
                        "pull_request": {"$ref": "#/definitions/prTrigger"},
                        "schedule": {"$ref": "#/definitions/scheduleTrigger"},
                        "workflow_dispatch": {"$ref": "#/definitions/workflowDispatch"},
                    },
                },
            ]
        },
        "env": {"type": "object", "additionalProperties": {"type": "string"}},
        "defaults": {
            "type": "object",
            "properties": {
                "run": {
                    "type": "object",
                    "properties": {
                        "shell": {"type": "string"},
                        "working-directory": {"type": "string"},
                    },
                },
            },
        },
        "concurrency": {
            "oneOf": [
                {"type": "string"},
                {
                    "type": "object",
                    "properties": {
                        "group": {"type": "string"},
                        "cancel-in-progress": {"type": "boolean"},
                    },
                    "required": ["group"],
                },
            ]
        },
        "jobs": {
            "type": "object",
            "additionalProperties": {"$ref": "#/definitions/job"},
            "minProperties": 1,
        },
    },
    "required": ["jobs"],
    "definitions": {
        "pushTrigger": {
            "oneOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "properties": {
                        "branches": {"type": "array", "items": {"type": "string"}},
                        "branches-ignore": {"type": "array", "items": {"type": "string"}},
                        "paths": {"type": "array", "items": {"type": "string"}},
                        "paths-ignore": {"type": "array", "items": {"type": "string"}},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "tags-ignore": {"type": "array", "items": {"type": "string"}},
                    },
                },
            ]
        },
        "prTrigger": {
            "oneOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "properties": {
                        "branches": {"type": "array", "items": {"type": "string"}},
                        "branches-ignore": {"type": "array", "items": {"type": "string"}},
                        "paths": {"type": "array", "items": {"type": "string"}},
                        "paths-ignore": {"type": "array", "items": {"type": "string"}},
                        "types": {"type": "array", "items": {"type": "string"}},
                    },
                },
            ]
        },
        "scheduleTrigger": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "cron": {"type": "string"},
                },
                "required": ["cron"],
            },
        },
        "workflowDispatch": {
            "oneOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "properties": {
                        "inputs": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "object",
                                "properties": {
                                    "description": {"type": "string"},
                                    "required": {"type": "boolean"},
                                    "default": {},
                                    "type": {
                                        "type": "string",
                                        "enum": ["string", "boolean", "choice", "environment"],
                                    },
                                    "options": {"type": "array", "items": {"type": "string"}},
                                },
                            },
                        },
                    },
                },
            ]
        },
        "job": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "runs-on": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}},
                    ]
                },
                "needs": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}},
                    ]
                },
                "if": {"type": "string"},
                "container": {"$ref": "#/definitions/container"},
                "services": {
                    "type": "object",
                    "additionalProperties": {"$ref": "#/definitions/container"},
                },
                "env": {"type": "object", "additionalProperties": {"type": "string"}},
                "steps": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/step"},
                    "minItems": 1,
                },
                "strategy": {"$ref": "#/definitions/strategy"},
                "timeout-minutes": {"type": "integer", "minimum": 1},
                "outputs": {"type": "object"},
            },
            "required": ["runs-on", "steps"],
        },
        "container": {
            "oneOf": [
                {"type": "string"},
                {
                    "type": "object",
                    "properties": {
                        "image": {"type": "string"},
                        "credentials": {
                            "type": "object",
                            "properties": {
                                "username": {"type": "string"},
                                "password": {"type": "string"},
                            },
                        },
                        "env": {"type": "object", "additionalProperties": {"type": "string"}},
                        "ports": {"type": "array", "items": {"type": ["string", "integer"]}},
                        "volumes": {"type": "array", "items": {"type": "string"}},
                        "options": {"type": "string"},
                    },
                    "required": ["image"],
                },
            ]
        },
        "strategy": {
            "type": "object",
            "properties": {
                "fail-fast": {"type": "boolean"},
                "max-parallel": {"type": "integer", "minimum": 1},
                "matrix": {
                    "type": "object",
                    "properties": {
                        "include": {"type": "array"},
                        "exclude": {"type": "array"},
                    },
                    "additionalProperties": {"type": "array"},
                },
            },
        },
        "step": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "id": {"type": "string"},
                "run": {"type": "string"},
                "uses": {"type": "string"},
                "with": {"type": "object"},
                "env": {"type": "object", "additionalProperties": {"type": "string"}},
                "working-directory": {"type": "string"},
                "shell": {"type": "string"},
                "if": {"type": "string"},
                "continue-on-error": {"type": "boolean"},
                "timeout-minutes": {"type": "integer", "minimum": 1},
            },
        },
    },
}


class SchemaValidator:
    """JSON Schema validator for pipeline configurations."""

    def __init__(self):
        self.validator = Draft7Validator(PIPELINE_SCHEMA)

    def validate(self, config: dict) -> list[str]:
        """
        Validate configuration against schema.

        Returns:
            list of validation error messages
        """
        errors = []

        for error in self.validator.iter_errors(config):
            path = " -> ".join(str(p) for p in error.absolute_path)
            if path:
                errors.append(f"{path}: {error.message}")
            else:
                errors.append(error.message)

        return errors


def validate_pipeline_schema(config: dict) -> list[str]:
    """
    Convenience function to validate pipeline configuration.

    Args:
        config: Parsed configuration dictionary

    Returns:
        list of validation error messages
    """
    validator = SchemaValidator()
    return validator.validate(config)
