"""Quick-and-dirty project complexity metrics.

Outputs (stdout JSON):
- total_files: Counted source files (Python + TS/TSX + Swift + HTML + CSS + config subset)
- sloc: Non-empty, non-comment physical source lines
- comments: Comment lines counted
- avg_sloc_per_file
- file_type_breakdown: Per extension SLOC
- top_files_by_sloc: Top N (default 10) largest files
- ruff_warnings (optional): If ruff installed, run a fast check count

Usage:
  python backend/scripts/project_metrics.py [--root .] [--top 10] [--json] [--details]

Limitations: heuristic comment detection, ignores vendored/minified assets.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

COMMENT_PATTERNS = {
    ".py": re.compile(r"^\s*#"),
    ".ts": re.compile(r"^\s*//"),
    ".tsx": re.compile(r"^\s*//"),
    ".js": re.compile(r"^\s*//"),
    ".swift": re.compile(r"^\s*//"),
    ".html": re.compile(r"^\s*<!--"),
    ".css": re.compile(r"^\s*/\*"),
}

SOURCE_EXTS = {".py", ".ts", ".tsx", ".js", ".swift", ".html", ".css"}
EXCLUDE_DIRS = {"node_modules", ".venv", "venv", "dist", "build", "__pycache__",
                ".pytest_cache", ".ruff_cache", ".mypy_cache"}
EXCLUDE_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
}

@dataclass
class FileMetrics:
    path: Path
    sloc: int
    comments: int
    total: int
    ext: str


def collect_file_metrics(path: Path) -> FileMetrics | None:
    ext = path.suffix.lower()
    if ext not in SOURCE_EXTS:
        return None
    sloc = comments = total = 0
    pattern = COMMENT_PATTERNS.get(ext)
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                total += 1
                stripped = line.strip()
                if not stripped:
                    continue
                if pattern and pattern.search(line):
                    comments += 1
                    continue
                # Very naive block comment handling for /* */ single-line starts
                if ext in {".css", ".js", ".ts", ".tsx"} and stripped.startswith("/*"):
                    comments += 1
                    continue
                sloc += 1
    except Exception:
        return None
    return FileMetrics(path=path, sloc=sloc, comments=comments, total=total, ext=ext)


def walk(root: Path) -> list[FileMetrics]:
    metrics: list[FileMetrics] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # prune
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith('.')]
        for filename in filenames:
            p = Path(dirpath) / filename
            fm = collect_file_metrics(p)
            if fm:
                metrics.append(fm)
    return metrics


def run_ruff_count(root: Path) -> int | None:
    try:
        proc = subprocess.run([
            "ruff", "check", str(root), "--quiet", "--output-format", "json"
        ], capture_output=True, text=True, check=False)
        if proc.returncode not in (0, 1):  # 0 = clean, 1 = lint issues
            return None
        if not proc.stdout.strip():
            return 0
        data = json.loads(proc.stdout)
        return len(data)
    except FileNotFoundError:
        return None


def load_coverage(coverage_json: Path) -> dict | None:
    if not coverage_json.exists():
        return None
    try:
        with coverage_json.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # Coverage JSON schema from pytest-cov (coverage.py) includes files dict
        files = data.get("files", {})
        total_stat = data.get("totals", {})
        percent = total_stat.get("percent_covered") or total_stat.get("percent_covered_display")
        return {
            "percent_covered": percent,
            "num_files": len(files),
        }
    except Exception:
        return None


def compute(metrics: list[FileMetrics], top_n: int) -> dict:
    if not metrics:
        return {"total_files": 0}
    total_files = len(metrics)
    total_sloc = sum(m.sloc for m in metrics)
    total_comments = sum(m.comments for m in metrics)
    breakdown: dict[str, int] = {}
    for m in metrics:
        breakdown[m.ext] = breakdown.get(m.ext, 0) + m.sloc
    top_files = sorted(metrics, key=lambda m: m.sloc, reverse=True)[:top_n]
    return {
        "total_files": total_files,
        "sloc": total_sloc,
        "comments": total_comments,
        "avg_sloc_per_file": round(total_sloc / total_files, 2),
        "file_type_breakdown": breakdown,
        "top_files_by_sloc": [
            {"path": str(m.path), "sloc": m.sloc, "comments": m.comments} for m in top_files
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute rough project complexity metrics")
    parser.add_argument("--root", default=".", help="Root directory to scan (project root)")
    parser.add_argument("--top", type=int, default=10, help="Top N largest files")
    parser.add_argument("--json", action="store_true", help="Output only JSON")
    parser.add_argument("--details", action="store_true", help="List every file metric")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    metrics = walk(root)
    result = compute(metrics, args.top)
    cov = load_coverage(Path("backend/coverage.json"))
    if cov:
        result["coverage"] = cov
    ruff_count = run_ruff_count(root)
    if ruff_count is not None:
        result["ruff_warnings"] = ruff_count

    if args.details:
        result["files"] = [
            {
                "path": str(m.path),
                "sloc": m.sloc,
                "comments": m.comments,
                "total": m.total,
                "ext": m.ext,
            }
            for m in sorted(metrics, key=lambda x: x.path.as_posix())
        ]

    out = json.dumps(result, indent=2)
    if args.json:
        print(out)
    else:
        print(out)
        print("\nSummary:")
        summary_line = (
            "Files: {files}  SLOC: {sloc}  Comments: {comments}  Avg/File: {avg}  Ruff: "
            "{ruff}".format(
                files=result["total_files"],
                sloc=result.get("sloc", 0),
                comments=result.get("comments", 0),
                avg=result.get("avg_sloc_per_file"),
                ruff=result.get("ruff_warnings"),
            )
        )
        print(summary_line)
        print("Top files:")
        for tf in result.get("top_files_by_sloc", []):
            print(f"  {tf['sloc']:5d}  {tf['path']}")

if __name__ == "__main__":
    main()
