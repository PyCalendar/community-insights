"""The CI runs every check of the Makefile, with the same make command."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
MAKEFILE = (ROOT / "Makefile").read_text()
WORKFLOW = (ROOT / ".github" / "workflows" / "tests.yml").read_text()

TEST_ALL = re.search(r"^test-all:([^#\n]*)", MAKEFILE, re.MULTILINE)
CHECKS = TEST_ALL.group(1).split() if TEST_ALL else []
RUN_IN_CI = set(re.findall(r"run: make ([\w-]+)", WORKFLOW))
TARGETS = set(re.findall(r"^([\w-]+):", MAKEFILE, re.MULTILINE))
JOBS = re.findall(r"^  ([\w-]+):\n", WORKFLOW.split("\njobs:\n", 1)[-1], re.MULTILINE)
NEEDED_FOR_PUSH = re.search(r"needs: \[([^\]]*)\]", WORKFLOW)
# changelog: only for pull requests; linkcheck and graphql: other sites can be down;
# deploy: runs after push
NOT_NEEDED_FOR_PUSH = {"changelog", "linkcheck", "graphql", "push", "deploy"}


def test_test_all_lists_the_checks():
    """Test all lists the checks."""
    assert {"docs", "vale", "linkcheck", "test", "lint"} <= set(CHECKS)


@pytest.mark.parametrize("check", CHECKS)
def test_check_is_a_target(check):
    """Check is a target."""
    assert check in TARGETS


@pytest.mark.parametrize("check", CHECKS)
def test_check_runs_in_the_ci(check):
    """Check runs in the ci."""
    assert check in RUN_IN_CI, f"add a job with 'run: make {check}' to tests.yml"


@pytest.mark.parametrize("target", ["livehtml", "linkcheck", "vale", "docs"])
def test_documentation_targets(target):
    """Documentation targets."""
    assert target in TARGETS


def test_vale_fails_on_errors():
    """Vale fails on errors."""
    vale = re.search(r"^vale:.*?\n\n", MAKEFILE, re.MULTILINE | re.DOTALL)
    assert vale
    assert "--no-exit" not in vale.group(0)


def test_docs_fail_on_warnings_and_broken_references():
    """Docs fail on warnings and broken references."""
    docs = re.search(r"^docs:.*?\n\n", MAKEFILE, re.MULTILINE | re.DOTALL)
    assert docs
    assert " -W " in docs.group(0)
    assert " -n " in docs.group(0)


def test_the_image_is_pushed_only_after_the_tests():
    """The image is pushed only after the tests."""
    assert NEEDED_FOR_PUSH
    needed = {job.strip() for job in NEEDED_FOR_PUSH.group(1).split(",")}
    assert needed == set(JOBS) - NOT_NEEDED_FOR_PUSH


def test_the_deployment_waits_for_the_pushed_image():
    """The deployment starts only after the image of the passed tests is pushed."""
    deploy = re.search(r"^  deploy:\n(.*?)(?=^  \w|\Z)", WORKFLOW, re.MULTILINE | re.DOTALL)
    assert deploy
    assert "needs: [push]" in deploy.group(1)
    assert "if: github.event_name == 'push'" in deploy.group(1)
    # the secret SENCHO_TOKEN is only given to jobs of its environment
    assert "name: insight.pycal.org" in deploy.group(1)
    assert "${{ secrets.SENCHO_TOKEN }}" in deploy.group(1)


def test_every_step_has_a_name():
    """The steps of the jobs are listed by their names on GitHub."""
    steps = re.findall(r"^ {6}- (\w+):", WORKFLOW, re.MULTILINE)
    assert steps
    assert set(steps) == {"name"}
