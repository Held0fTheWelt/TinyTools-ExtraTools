"""Tests for fixtures autark.

"""
from __future__ import annotations

from pathlib import Path


def create_target_repo(base: Path) -> Path:
    """Create target repo.

    This callable writes or records artifacts as part of its workflow.

    Args:
        base: Primary base used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    repo = base / 'target_repo'
    (repo / 'src').mkdir(parents=True, exist_ok=True)
    (repo / 'docs' / 'api').mkdir(parents=True, exist_ok=True)
    (repo / 'docs' / 'ADR').mkdir(parents=True, exist_ok=True)
    (repo / 'tests').mkdir(parents=True, exist_ok=True)
    (repo / '.github' / 'workflows').mkdir(parents=True, exist_ok=True)
    (repo / 'docs').mkdir(exist_ok=True)

    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (repo / 'pyproject.toml').write_text('[project]\nname = "toy-target"\nversion = "0.1.0"\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (repo / 'src' / 'app.py').write_text(
        'def hello(name: str):\n    return f"Hello, {name}"\n\nclass Service:\n    def run(self):\n        return 1\n',
        encoding='utf-8',
    )
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (repo / 'tests' / 'run_tests.py').write_text('TEST_TARGETS = {"unit": ["tests"]}\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (repo / 'tests' / 'test_health_contract.py').write_text(
        'def test_health_contract_marker():\n    assert True\n',
        encoding='utf-8',
    )
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (repo / '.github' / 'workflows' / 'ci.yml').write_text(
        'name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n',
        encoding='utf-8',
    )
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (repo / 'docs' / 'README.md').write_text('# Toy Target\n\nA tiny repo for adapter testing.\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (repo / 'docs' / 'ADR' / 'ADR-0001-consolidated-health-contract.md').write_text(
        '# ADR-0001: Consolidated Health Contract\n\nStatus: Accepted\nDate: 2026-04-17\nSupersedes: ADR-0000\n\nThis consolidated ADR defines the health API contract and test reflection requirement.\n',
        encoding='utf-8',
    )
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (repo / 'docs' / 'api' / 'openapi.yaml').write_text(
        'openapi: 3.0.0\ninfo:\n  title: Toy API\n  version: 1.0.0\npaths:\n  /health:\n    get:\n      tags: [system]\n      summary: Health\n      responses:\n        "200":\n          description: OK\n',
        encoding='utf-8',
    )
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (repo / 'docker-compose.yml').write_text('services:\n  app:\n    image: python:3.11\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (repo / 'docker-up.py').write_text('print("docker up")\n', encoding='utf-8')

    # minimal UI surfaces for templatify/usabilify
    (repo / 'frontend' / 'templates').mkdir(parents=True, exist_ok=True)
    (repo / 'administration-tool' / 'templates' / 'manage').mkdir(parents=True, exist_ok=True)
    (repo / 'backend' / 'app' / 'info' / 'templates').mkdir(parents=True, exist_ok=True)
    (repo / 'writers-room' / 'app' / 'templates').mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (repo / 'frontend' / 'templates' / 'base.html').write_text(
        '<!doctype html><html><body><nav></nav><main>{% block content %}{% endblock %}</main></body></html>',
        encoding='utf-8',
    )
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (repo / 'frontend' / 'templates' / 'login.html').write_text(
        '{% extends "base.html" %}{% block content %}<h1>Login</h1><form><label>User</label><input aria-label="username"></form>{% endblock %}',
        encoding='utf-8',
    )
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (repo / 'administration-tool' / 'templates' / 'base.html').write_text(
        '<!doctype html><html><body><nav></nav><main>{% block content %}{% endblock %}</main></body></html>',
        encoding='utf-8',
    )
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (repo / 'administration-tool' / 'templates' / 'manage' / 'base.html').write_text(
        '<!doctype html><html><body><nav></nav><main>{% block content %}{% endblock %}</main></body></html>',
        encoding='utf-8',
    )
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (repo / 'backend' / 'app' / 'info' / 'templates' / 'base.html').write_text(
        '<!doctype html><html><body><main>{% block content %}{% endblock %}</main></body></html>',
        encoding='utf-8',
    )
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (repo / 'writers-room' / 'app' / 'templates' / 'base.html').write_text(
        '<!doctype html><html><body><main>{% block content %}{% endblock %}</main></body></html>',
        encoding='utf-8',
    )

    (repo / 'docs' / 'dev').mkdir(parents=True, exist_ok=True)
    (repo / 'docs' / 'technical' / 'architecture').mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (repo / 'docs' / 'dev' / 'play_shell_ux.md').write_text(
        '# Play Shell UX\n\n- The player must always see clear status feedback.\n- Keyboard navigation should remain possible in core views.\n',
        encoding='utf-8',
    )
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (repo / 'docs' / 'technical' / 'architecture' / 'session_runtime_contract.md').write_text(
        '# Session Runtime Contract\n\n- The console should expose status and error feedback.\n',
        encoding='utf-8',
    )
    return repo
