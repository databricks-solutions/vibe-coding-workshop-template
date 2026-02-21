"""
Genie Space Benchmark SQL Validation Module

Extracts benchmark SQL from Genie Space JSON configurations, substitutes
template variables, executes each query with LIMIT 1, and returns a
structured validation report.

Usage:
    from validate_genie_benchmark_sql import validate_benchmarks

    report = validate_benchmarks(
        spark=spark,
        config_path="/path/to/genie_space_config.json",
        variables={"catalog": "my_catalog", "gold_schema": "gold"}
    )
"""

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BenchmarkResult:
    question: str
    sql: str
    status: str  # "PASS", "FAIL", "ERROR"
    error_message: str = ""
    error_category: str = ""  # "SYNTAX", "RESOLUTION", "PERMISSION", "RUNTIME"


@dataclass
class ValidationReport:
    config_file: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    results: list = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return (self.passed / self.total * 100) if self.total > 0 else 0.0

    def summary(self) -> str:
        lines = [
            f"Benchmark Validation: {self.config_file}",
            f"  Total: {self.total} | Passed: {self.passed} | Failed: {self.failed} | Errors: {self.errors}",
            f"  Success Rate: {self.success_rate:.1f}%",
        ]
        for r in self.results:
            icon = "✅" if r.status == "PASS" else "❌"
            lines.append(f"  {icon} {r.question[:80]}")
            if r.error_message:
                lines.append(f"     → [{r.error_category}] {r.error_message[:120]}")
        return "\n".join(lines)


def _categorize_error(error_msg: str) -> str:
    """Classify SQL errors into actionable categories."""
    msg = error_msg.upper()
    if any(kw in msg for kw in ["PARSE_SYNTAX_ERROR", "SYNTAX ERROR", "PARSE ERROR"]):
        return "SYNTAX"
    if any(kw in msg for kw in ["TABLE_OR_VIEW_NOT_FOUND", "CANNOT RESOLVE", "COLUMN"]):
        return "RESOLUTION"
    if any(kw in msg for kw in ["PERMISSION", "ACCESS DENIED", "INSUFFICIENT"]):
        return "PERMISSION"
    return "RUNTIME"


def _substitute_variables(text: str, variables: dict) -> str:
    """Replace ${var} patterns in text."""
    for key, value in variables.items():
        text = text.replace(f"${{{key}}}", value)
    return text


def _extract_benchmarks(config: dict) -> list[dict]:
    """Extract benchmark questions from Genie Space JSON.

    Handles both raw space config and wrapped (serialized_space) formats.
    """
    space = config
    if "serialized_space" in config:
        serialized = config["serialized_space"]
        if isinstance(serialized, str):
            space = json.loads(serialized)
        else:
            space = serialized
    elif "space" in config and "serialized_space" in config.get("space", {}):
        serialized = config["space"]["serialized_space"]
        if isinstance(serialized, str):
            space = json.loads(serialized)
        else:
            space = serialized

    return space.get("example_question_sqls", [])


def validate_benchmarks(
    spark,
    config_path: str,
    variables: dict,
) -> ValidationReport:
    """Validate all benchmark SQL in a Genie Space config file.

    Args:
        spark: SparkSession instance
        config_path: Path to the Genie Space JSON config file
        variables: Dict of template variables (e.g., {"catalog": "main", "gold_schema": "gold"})

    Returns:
        ValidationReport with per-query results
    """
    path = Path(config_path)
    report = ValidationReport(config_file=path.name)

    with open(path, "r") as f:
        config = json.load(f)

    benchmarks = _extract_benchmarks(config)
    report.total = len(benchmarks)

    for bm in benchmarks:
        question_raw = bm.get("question", ["(no question)"])
        question = question_raw[0] if isinstance(question_raw, list) else question_raw

        sql_parts = []
        for answer in bm.get("answer", []):
            if answer.get("format") == "SQL":
                content = answer.get("content", [])
                if isinstance(content, list):
                    sql_parts.extend(content)
                else:
                    sql_parts.append(str(content))

        if not sql_parts:
            report.errors += 1
            report.results.append(
                BenchmarkResult(
                    question=question,
                    sql="",
                    status="ERROR",
                    error_message="No SQL found in answer",
                    error_category="RESOLUTION",
                )
            )
            continue

        sql = " ".join(sql_parts)
        sql = _substitute_variables(sql, variables)

        limited_sql = f"SELECT * FROM ({sql}) AS _validation_query LIMIT 1"

        try:
            spark.sql(limited_sql).collect()
            report.passed += 1
            report.results.append(
                BenchmarkResult(question=question, sql=sql, status="PASS")
            )
        except Exception as e:
            error_msg = str(e)
            category = _categorize_error(error_msg)
            report.failed += 1
            report.results.append(
                BenchmarkResult(
                    question=question,
                    sql=sql,
                    status="FAIL",
                    error_message=error_msg,
                    error_category=category,
                )
            )

    return report
