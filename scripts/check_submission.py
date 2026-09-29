#!/usr/bin/env python3
"""Pre-submission checks for CivicPulse (CS4032 Assignment 01, §5.3).

This is a lint, not a grader (the assignment PDF says so explicitly): it
catches the mechanical failures behind most of the automatic deductions in
§5.3, nothing more. A clean run does not guarantee a good mark; a dirty run
nearly guarantees a bad one.

Usage:
    python scripts/check_submission.py

Exit code is non-zero if any check fails, so it's safe to wire into a
pre-commit hook or a CI step if you want an even earlier signal than
ci.yml's own checks.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FAILURES: list[str] = []
WARNINGS: list[str] = []


def fail(message: str) -> None:
    FAILURES.append(message)


def warn(message: str) -> None:
    WARNINGS.append(message)


def iter_tracked_files() -> list[Path]:
    """Files git actually tracks — the only things that matter for most of
    these checks. Falls back to a manual walk (skipping the usual noise
    directories) if this isn't a git repo yet."""
    try:
        out = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return [ROOT / line for line in out.splitlines() if line.strip()]
    except (subprocess.CalledProcessError, FileNotFoundError):
        warn("Not a git repository (or git isn't installed) — falling back to a manual "
             "file walk. Run this again after `git init` for the real check.")
        skip_dirs = {".git", "node_modules", "dist", "__pycache__", ".venv"}
        return [
            p for p in ROOT.rglob("*")
            if p.is_file() and not any(part in skip_dirs for part in p.parts)
        ]


def check_no_env_committed(files: list[Path]) -> None:
    """§5.3: 'A .env, key, token or password anywhere in Git history — −20'.
    This only checks the current tree, not full history — see the note
    printed at the end about scanning history separately."""
    for f in files:
        if f.name == ".env" or (f.name.startswith(".env.") and f.name != ".env.example"):
            fail(f"{f.relative_to(ROOT)} is tracked by git — .env must be gitignored, "
                 "only .env.example should be committed.")


def check_unpinned_images(files: list[Path]) -> None:
    """§5.3: 'Unpinned base image, or postgres / redis / node without a tag — −8'."""
    image_line = re.compile(r"^\s*(?:image|FROM)\s*:?\s+([^\s#]+)", re.IGNORECASE)
    for f in files:
        if f.name not in ("compose.yaml", "compose.prod.yaml", "Dockerfile") and not (
            f.suffix == ".yaml" and "k8s" in f.parts
        ):
            continue
        try:
            text = f.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            m = image_line.match(line)
            if not m:
                continue
            ref = m.group(1)
            if ref.startswith("$") or ref.startswith("${"):
                continue  # CI-substituted — checked separately, not a literal tag
            if ":latest" in ref:
                fail(f"{f.relative_to(ROOT)}:{lineno} references `:latest` ({ref}) — "
                     "pin to a specific version.")
            elif ":" not in ref.split("/")[-1]:
                fail(f"{f.relative_to(ROOT)}:{lineno} has no tag at all ({ref}) — "
                     "an implicit `:latest` is the same deduction.")


def check_localhost_in_service_config(files: list[Path]) -> None:
    """§5.3: 'localhost used for service-to-service communication — −8'.
    Flags localhost/127.0.0.1 in compose/k8s config where a service name
    should be used instead. Healthcheck probes hitting their own container
    are fine and excluded."""
    own_probe = re.compile(r"(wget|curl|python).*127\.0\.0\.1|localhost", re.IGNORECASE)
    for f in files:
        if f.name not in ("compose.yaml", "compose.prod.yaml") and not (
            f.suffix == ".yaml" and "k8s" in f.parts
        ):
            continue
        try:
            text = f.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if ("localhost" in line or "127.0.0.1" in line) and not own_probe.search(line):
                warn(f"{f.relative_to(ROOT)}:{lineno} mentions localhost/127.0.0.1 — "
                     "confirm this is a self-healthcheck, not cross-service "
                     "communication (which must use the service name).")


def check_frontend_reaches_database(files: list[Path]) -> None:
    """§5.3: 'Frontend able to reach the database — network segmentation not
    implemented — −8'. Checks that compose.yaml's frontend service is not on
    the internal network."""
    compose = ROOT / "compose.yaml"
    if not compose.exists():
        warn("compose.yaml not found — skipping network segmentation check.")
        return
    try:
        import yaml
    except ImportError:
        warn("PyYAML not installed — skipping network segmentation check "
             "(pip install --break-system-packages pyyaml).")
        return
    doc = yaml.safe_load(compose.read_text())
    frontend = (doc.get("services", {}) or {}).get("frontend", {})
    frontend_networks = set(frontend.get("networks", []) or [])
    if "internal" in frontend_networks:
        fail("compose.yaml: frontend is attached to the `internal` network — "
             "it must only be on `edge`, or it can reach postgres/redis directly.")


def check_no_published_db_cache_port_in_prod(files: list[Path]) -> None:
    """§5.3: 'Published database or cache port in compose.prod.yaml ... −8'."""
    prod = ROOT / "compose.prod.yaml"
    if not prod.exists():
        return
    try:
        import yaml
    except ImportError:
        return
    doc = yaml.safe_load(prod.read_text())
    for name in ("postgres", "redis"):
        svc = (doc.get("services", {}) or {}).get(name, {})
        if svc.get("ports"):
            fail(f"compose.prod.yaml: `{name}` publishes a port ({svc['ports']}) — "
                 "database/cache ports must never be published in prod.")


def check_no_build_key_in_prod(files: list[Path]) -> None:
    """§3.2: 'compose.prod.yaml uses image: ${IMAGE_TAG}, no build: ... −1' (§G rubric)."""
    prod = ROOT / "compose.prod.yaml"
    if not prod.exists():
        return
    try:
        import yaml
    except ImportError:
        return
    doc = yaml.safe_load(prod.read_text())
    for name, svc in (doc.get("services", {}) or {}).items():
        if "build" in svc:
            fail(f"compose.prod.yaml: service `{name}` has a `build:` key — "
                 "prod must reference pre-built images only.")


def check_no_deploying_latest_in_workflows(files: list[Path]) -> None:
    """§5.3: 'Deploying :latest anywhere — −8'. Checks cd.yml/release.yml
    don't apply manifests with :latest as the deployed tag."""
    for f in files:
        if f.name not in ("cd.yml", "release.yml"):
            continue
        text = f.read_text()
        if re.search(r"set image[^\n]*:latest", text):
            fail(f"{f.relative_to(ROOT)}: `kustomize edit set image` targets `:latest` — "
                 "deploy by commit SHA, not latest.")


def check_needs_gating(files: list[Path]) -> None:
    """§5.3: 'Publishing or deploying job not gated by needs: — −8'."""
    try:
        import yaml
    except ImportError:
        warn("PyYAML not installed — skipping needs: gating check.")
        return
    publishing_keywords = ("push", "deploy", "release")
    for f in files:
        if f.parent.name != "workflows" or f.suffix != ".yml":
            continue
        doc = yaml.safe_load(f.read_text())
        for job_name, job in (doc.get("jobs", {}) or {}).items():
            if any(kw in job_name.lower() for kw in publishing_keywords) and "needs" not in job:
                fail(f"{f.relative_to(ROOT)}: job `{job_name}` looks like a "
                     "publish/deploy job but has no `needs:` gate.")


def check_secrets_are_placeholders(files: list[Path]) -> None:
    """§5.3: 'An LLM API key in a committed Kubernetes manifest, even
    base64-encoded ... −15'. Flags anything in k8s/**/secret.yaml that
    isn't an obvious placeholder."""
    secret = ROOT / "k8s" / "base" / "secret.yaml"
    if not secret.exists():
        return
    try:
        import yaml
    except ImportError:
        return
    doc = yaml.safe_load(secret.read_text())
    for key, value in (doc.get("stringData", {}) or {}).items():
        if "REPLACE" not in str(value) and "CHANGE" not in str(value).upper():
            fail(f"k8s/base/secret.yaml: `{key}` does not look like a placeholder "
                 f"(got {value!r}) — committed manifests must carry placeholders only.")
    for key, value in (doc.get("data", {}) or {}).items():
        fail(f"k8s/base/secret.yaml: `{key}` is base64-encoded data, not a placeholder — "
             "base64 is encoding, not encryption, and this is the same −15 as plaintext.")


def check_dockerignore_present(files: list[Path]) -> None:
    for ctx in ("frontend", "backend"):
        dockerfile = ROOT / ctx / "Dockerfile"
        dockerignore = ROOT / ctx / ".dockerignore"
        if dockerfile.exists() and not dockerignore.exists():
            fail(f"{ctx}/Dockerfile exists but {ctx}/.dockerignore does not.")


def main() -> int:
    files = iter_tracked_files()

    check_no_env_committed(files)
    check_unpinned_images(files)
    check_localhost_in_service_config(files)
    check_frontend_reaches_database(files)
    check_no_published_db_cache_port_in_prod(files)
    check_no_build_key_in_prod(files)
    check_no_deploying_latest_in_workflows(files)
    check_needs_gating(files)
    check_secrets_are_placeholders(files)
    check_dockerignore_present(files)

    print(f"Checked {len(files)} tracked files.\n")

    if WARNINGS:
        print("Warnings (check by hand):")
        for w in WARNINGS:
            print(f"  ! {w}")
        print()

    if FAILURES:
        print("Failures:")
        for f in FAILURES:
            print(f"  x {f}")
        print(f"\n{len(FAILURES)} check(s) failed.")
        return 1

    print("All automated checks passed.")
    print(
        "\nNot checked here — do these by hand before submitting:\n"
        "  - .env/keys/tokens/passwords anywhere in *git history*, not just the "
        "current tree (`git log -p -- .env` and `git log --all --full-history -- '**/.env'`)\n"
        "  - localhost used for service-to-service calls in application code "
        "(this script only scans compose/k8s YAML)\n"
        "  - PostgreSQL as a Deployment with no PVC (only relevant if you add a "
        "second, non-StatefulSet postgres manifest — the base one here is a "
        "StatefulSet)\n"
        "  - commits pushed directly to main (`git log main --not --remotes` or "
        "check the branch protection settings on GitHub directly)\n"
        "  - README quickstart working from an actual clean clone, not just this tree"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
