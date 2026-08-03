from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from typing import Literal

from edgar_qa.api.models import AnswerResponse, FeedbackRequest

MetricUnit = Literal["Count", "Milliseconds", "None"]


@dataclass(frozen=True)
class MetricDatum:
    value: int | float
    unit: MetricUnit


@dataclass(frozen=True)
class MetricsConfig:
    namespace: str
    service: str
    environment: str


def emit_request_metrics(
    config: MetricsConfig,
    *,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
) -> None:
    metrics = {
        "RequestCount": MetricDatum(1, "Count"),
        "RequestLatency": MetricDatum(round(duration_ms, 2), "Milliseconds"),
    }
    if 400 <= status_code < 500:
        metrics["ClientErrorCount"] = MetricDatum(1, "Count")
    if status_code >= 500:
        metrics["ServerErrorCount"] = MetricDatum(1, "Count")
    emit_emf(
        config,
        metrics=metrics,
        properties={
            "EventType": "http_request",
            "Method": method,
            "Path": path,
            "StatusCode": status_code,
        },
    )


def emit_answer_metrics(config: MetricsConfig, response: AnswerResponse) -> None:
    metrics = {
        "AnswerCount": MetricDatum(1, "Count"),
        "AnswerLatency": MetricDatum(response.latency_ms, "Milliseconds"),
        "ModelCallCount": MetricDatum(response.model_calls, "Count"),
    }
    if response.abstained:
        metrics["AbstentionCount"] = MetricDatum(1, "Count")
    if response.revised:
        metrics["RevisionCount"] = MetricDatum(1, "Count")
    if not response.citation_valid:
        metrics["CitationFailureCount"] = MetricDatum(1, "Count")
    if response.total_tokens is not None:
        metrics["TokenCount"] = MetricDatum(response.total_tokens, "Count")
    emit_emf(
        config,
        metrics=metrics,
        properties={
            "EventType": "answer",
            "RequestId": response.request_id,
            "Abstained": response.abstained,
            "Revised": response.revised,
            "CitationValid": response.citation_valid,
        },
    )


def emit_feedback_metrics(
    config: MetricsConfig,
    *,
    feedback_id: str,
    feedback: FeedbackRequest,
) -> None:
    metrics = {"FeedbackCount": MetricDatum(1, "Count")}
    if not feedback.helpful:
        metrics["NegativeFeedbackCount"] = MetricDatum(1, "Count")
    emit_emf(
        config,
        metrics=metrics,
        properties={
            "EventType": "feedback",
            "FeedbackId": feedback_id,
            "AnswerRequestId": feedback.request_id,
            "Helpful": feedback.helpful,
            "Reason": feedback.reason,
        },
    )


def emit_emf(
    config: MetricsConfig,
    *,
    metrics: dict[str, MetricDatum],
    properties: dict[str, object],
) -> None:
    """Write one valid CloudWatch Embedded Metric Format JSON event."""
    payload: dict[str, object] = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": config.namespace,
                    "Dimensions": [["Service", "Environment"]],
                    "Metrics": [
                        {"Name": name, "Unit": datum.unit} for name, datum in metrics.items()
                    ],
                }
            ],
        },
        "Service": config.service,
        "Environment": config.environment,
        **properties,
    }
    payload.update({name: datum.value for name, datum in metrics.items()})
    sys.stdout.write(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    sys.stdout.write("\n")
    sys.stdout.flush()
