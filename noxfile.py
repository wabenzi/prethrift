"""Nox sessions for Prethrift backend.

Usage examples:
  nox -l                     # list sessions
  nox -s lint                # run lint session
  nox -s tests               # run tests (default Python)
  nox -s tests -- -k root    # pass args to pytest
  nox -s typecheck           # mypy
  nox -s format              # auto-format
  nox -s all                 # lint + type + tests
Add more Python versions in PYTHON_VERSIONS when needed.
"""

from __future__ import annotations

import os
import nox

PYTHON_VERSIONS: list[str] = ["3.13"]  # expand later if needed
BASE_REQ = "backend/requirements.txt"
PACKAGE_IMPORT_ROOT = "backend"


@nox.session(python=PYTHON_VERSIONS)
def lint(session: nox.Session) -> None:
    session.install("-r", BASE_REQ)
    session.run("ruff", "check", "backend/app", "backend/tests")
    session.run("ruff", "format", "--check", "backend/app", "backend/tests")


@nox.session(python=PYTHON_VERSIONS)
def format(session: nox.Session) -> None:
    session.install("-r", BASE_REQ)
    session.run("ruff", "format", "backend/app", "backend/tests")


@nox.session(python=PYTHON_VERSIONS)
def typecheck(session: nox.Session) -> None:
    session.install("-r", BASE_REQ)
    env = {"PYTHONPATH": os.getcwd()}
    session.run("mypy", "backend/app", env=env)


@nox.session(python=PYTHON_VERSIONS)
def tests(session: nox.Session) -> None:
    session.install("-r", BASE_REQ)
    env = {"PYTHONPATH": os.getcwd()}
    session.run("pytest", "-q", "backend/tests", *session.posargs, env=env)


@nox.session(python=PYTHON_VERSIONS)
def all(session: nox.Session) -> None:
    session.notify("lint")
    session.notify("typecheck")
    session.notify("tests")
