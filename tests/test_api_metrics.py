from __future__ import annotations

import json

from pytest import CaptureFixture

from edgar_qa.api.metrics import (
    MetricDatum,
    MetricsConfig,
    emit_emf,
    emit_request_metrics,
)


def test_emit_emf_writes_valid_metric_document(capsys: CaptureFixture[str]) -> None:
    config = MetricsConfig(
        namespace="SECQA",
        service="sec-filing-agentic-qa",
        environment="test",
    )
    emit_emf(
        config,
        metrics={"RequestCount": MetricDatum(1, "Count")},
        properties={"EventType": "test"},
    )
    output = capsys.readouterr().out
    payload = json.loads(output)
    directive = payload["_aws"]["CloudWatchMetrics"][0]
    assert directive["Namespace"] == "SECQA"
    assert directive["Dimensions"] == [["Service", "Environment"]]
    assert payload["RequestCount"] == 1


def test_request_metrics_include_server_error(capsys: CaptureFixture[str]) -> None:
    config = MetricsConfig(
        namespace="SECQA",
        service="sec-filing-agentic-qa",
        environment="test",
    )
    emit_request_metrics(
        config,
        method="POST",
        path="/v1/answer",
        status_code=502,
        duration_ms=123.4,
    )
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["ServerErrorCount"] == 1
    assert payload["RequestLatency"] == 123.4
