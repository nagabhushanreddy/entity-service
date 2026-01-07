import argparse
import os
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


def run_pytest(repo_root: Path, reports_dir: Path) -> int:
    reports_dir.mkdir(parents=True, exist_ok=True)
    junit_path = reports_dir / "junit.xml"
    coverage_xml = reports_dir / "coverage.xml"
    coverage_html_dir = reports_dir / "coverage-html"

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "tests",
        f"--junitxml={junit_path}",
        "--asyncio-mode=auto",
        "--cov=app",
        "--cov=main",
        f"--cov-report=xml:{coverage_xml}",
        f"--cov-report=html:{coverage_html_dir}",
        "--cov-report=term-missing",
    ]

    env = os.environ.copy()
    proc = subprocess.run(cmd, cwd=repo_root, env=env)
    return proc.returncode


def parse_junit(junit_file: Path) -> dict:
    if not junit_file.exists():
        return {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "time": 0.0}
    tree = ET.parse(junit_file)
    root = tree.getroot()
    if root.tag == "testsuites":
        tests = sum(int(ts.attrib.get("tests", 0)) for ts in root)
        failures = sum(int(ts.attrib.get("failures", 0)) for ts in root)
        errors = sum(int(ts.attrib.get("errors", 0)) for ts in root)
        skipped = sum(int(ts.attrib.get("skipped", 0)) for ts in root)
        time = sum(float(ts.attrib.get("time", 0.0)) for ts in root)
    else:
        tests = int(root.attrib.get("tests", 0))
        failures = int(root.attrib.get("failures", 0))
        errors = int(root.attrib.get("errors", 0))
        skipped = int(root.attrib.get("skipped", 0))
        time = float(root.attrib.get("time", 0.0))
    return {
        "tests": tests,
        "failures": failures,
        "errors": errors,
        "skipped": skipped,
        "time": time,
    }


def parse_coverage(coverage_xml: Path) -> float:
    if not coverage_xml.exists():
        return 0.0
    tree = ET.parse(coverage_xml)
    root = tree.getroot()
    line_rate = root.attrib.get("line-rate")
    try:
        return round(float(line_rate) * 100.0, 2) if line_rate is not None else 0.0
    except Exception:
        return 0.0


def write_markdown(report_md: Path, junit_stats: dict, coverage_pct: float) -> None:
    lines = []
    lines.append(f"# entity-api Test Report\n")
    lines.append(f"- Total tests: {junit_stats['tests']}\n")
    lines.append(f"- Failures: {junit_stats['failures']}\n")
    lines.append(f"- Errors: {junit_stats['errors']}\n")
    lines.append(f"- Skipped: {junit_stats['skipped']}\n")
    lines.append(f"- Duration (s): {round(junit_stats['time'], 3)}\n")
    lines.append(f"- Line coverage: {coverage_pct}%\n")
    report_md.write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Run entity-api tests and generate reports")
    parser.add_argument("--reports-dir", default="reports", help="Reports output directory")
    args = parser.parse_args()

    repo_root = Path(__file__).parent
    reports_dir = repo_root / args.reports_dir
    ret = run_pytest(repo_root, reports_dir)

    junit_stats = parse_junit(reports_dir / "junit.xml")
    coverage_pct = parse_coverage(reports_dir / "coverage.xml")
    write_markdown(reports_dir / "test-report.md", junit_stats, coverage_pct)

    print(f"JUnit XML: {reports_dir / 'junit.xml'}")
    print(f"Coverage XML: {reports_dir / 'coverage.xml'}")
    print(f"Coverage HTML: {reports_dir / 'coverage-html'}/index.html")
    print(f"Markdown Report: {reports_dir / 'test-report.md'}")
    sys.exit(ret)


if __name__ == "__main__":
    main()
