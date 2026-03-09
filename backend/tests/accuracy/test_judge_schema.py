from backend.tests.accuracy.judge_schema import JudgeResult, JudgeIssue


def test_judge_result_parses():
    r = JudgeResult(
        issues=[
            JudgeIssue(
                severity="critical",
                metric="GLUCOSA",
                field="value_numeric",
                expected="94.5",
                got="94.2",
                description="Value differs",
            )
        ],
        total_metrics_in_pdf=10,
        total_metrics_extracted=9,
    )
    assert len(r.issues) == 1
    assert r.issues[0].severity == "critical"
