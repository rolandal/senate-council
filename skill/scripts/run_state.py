#!/usr/bin/env python3
"""Resumable run checkpoints — so a Senate run that dies at Stage 3 doesn't restart from zero.

A full Senate run walks a fixed pipeline (frame -> prompts -> gate_inputs -> convene ->
gate_quorum -> tally -> committees -> briefs -> reviews -> verdict -> render). If the
process dies mid-run (rate limit, crash, killed terminal), ~36 completed member
responses would otherwise be discarded and re-run from scratch.

This script gives a run a checkpoint directory: a manifest.json tracking which
stages have a saved artifact, plus an artifacts/ folder holding copies of those
artifact files. The orchestrator calls `init` once, `save` after each stage
completes (copying that stage's output file in), and `status` to find out which
stage to resume from.

  python3 run_state.py init --slug relocation-senate
  python3 run_state.py save --run-dir DIR --stage convene --file responses.json
  python3 run_state.py status --run-dir DIR

All commands print JSON to stdout. `save`/`init --date` accept overrides so tests
never read the wall clock. Stdlib only.
"""
import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone

# Canonical Senate pipeline order. `status`/`save` use this to compute "next".
STAGES = (
    "frame",
    "prompts",
    "gate_inputs",
    "convene",
    "gate_quorum",
    "tally",
    "committees",
    "briefs",
    "reviews",
    "verdict",
    "render",
)

DEFAULT_RUN_ROOT = os.path.expanduser("~/Documents/Local/council-log/runs")


def _manifest_path(run_dir):
    return os.path.join(run_dir, "manifest.json")


def _load_manifest(run_dir):
    path = _manifest_path(run_dir)
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"corrupt manifest at {path}: {exc}. Stage artifacts (if any) are still "
            f"intact under {os.path.join(run_dir, 'artifacts')} — delete manifest.json, "
            "re-run init, and re-save the stages whose artifacts survived."
        )


def _save_manifest(run_dir, manifest):
    # Write-to-temp + atomic rename: a kill mid-save must never leave a
    # truncated manifest.json (this module exists to survive mid-run death).
    path = _manifest_path(run_dir)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(manifest, f, indent=2)
    os.replace(tmp, path)


def _next_stage(stages_done):
    for stage in STAGES:
        if stage not in stages_done:
            return stage
    return None


def _status(manifest):
    stages = manifest["stages"]
    return {
        "slug": manifest["slug"],
        "date": manifest["date"],
        "stages": stages,
        "next": _next_stage(stages),
        "complete": all(s in stages for s in STAGES),
    }


def init_run(slug, run_root=None, date=None):
    """Create (or reuse) DIR/<date>-<slug>/ with an empty manifest. Idempotent."""
    run_root = run_root or DEFAULT_RUN_ROOT
    date = date or datetime.now(timezone.utc).date().isoformat()
    run_dir = os.path.join(run_root, f"{date}-{slug}")
    manifest_path = _manifest_path(run_dir)
    if os.path.exists(manifest_path):
        manifest = _load_manifest(run_dir)
    else:
        os.makedirs(run_dir, exist_ok=True)
        manifest = {"slug": slug, "date": date, "stages": {}}
        _save_manifest(run_dir, manifest)
    status = _status(manifest)
    status["run_dir"] = run_dir
    return status


def save_stage(run_dir, stage, file_path, now=None):
    """Copy the stage's artifact into run_dir/artifacts/ and record it in the manifest."""
    if stage not in STAGES:
        raise SystemExit(
            f"unknown stage {stage!r}; valid stages are: {', '.join(STAGES)}"
        )
    manifest = _load_manifest(run_dir)
    artifacts_dir = os.path.join(run_dir, "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    dest_name = f"{stage}-{os.path.basename(file_path)}"
    dest_path = os.path.join(artifacts_dir, dest_name)
    shutil.copyfile(file_path, dest_path)
    saved_at = now or datetime.now(timezone.utc).isoformat()
    manifest["stages"][stage] = {
        "saved_at": saved_at,
        "artifact": os.path.join("artifacts", dest_name),
    }
    _save_manifest(run_dir, manifest)
    status = _status(manifest)
    status["run_dir"] = run_dir
    return status


def get_status(run_dir):
    manifest = _load_manifest(run_dir)
    return _status(manifest)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="create (or reuse) a run checkpoint directory")
    p_init.add_argument("--slug", required=True)
    p_init.add_argument("--run-root", default=None)
    p_init.add_argument("--date", default=None, help="YYYY-MM-DD (default: today)")

    p_save = sub.add_parser("save", help="save a completed stage's artifact")
    p_save.add_argument("--run-dir", required=True)
    p_save.add_argument("--stage", required=True)
    p_save.add_argument("--file", required=True, dest="file_path")
    p_save.add_argument("--now", default=None, help="ISO timestamp override")

    p_status = sub.add_parser("status", help="print run status and next stage to resume")
    p_status.add_argument("--run-dir", required=True)

    args = ap.parse_args()

    if args.command == "init":
        result = init_run(args.slug, run_root=args.run_root, date=args.date)
    elif args.command == "save":
        result = save_stage(args.run_dir, args.stage, args.file_path, now=args.now)
    elif args.command == "status":
        result = get_status(args.run_dir)
    else:
        raise SystemExit(f"unknown command {args.command!r}")

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
