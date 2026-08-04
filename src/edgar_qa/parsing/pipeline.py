from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import PurePosixPath
from typing import Any

from botocore.exceptions import ClientError

from edgar_qa.parsing.html_parser import SecHtmlDocumentParser
from edgar_qa.parsing.models import FilingIdentity, ParsingResult, ParsingStatus

_KEY_RE = re.compile(
    r"^filings/cik=(?P<cik>\d+)/form=(?P<form>[^/]+)/"
    r"filing_date=(?P<filing_date>[^/]+)/accession=(?P<accession>[^/]+)/"
    r"(?P<filename>[^/]+)$"
)


class InvalidRawFilingKeyError(ValueError):
    """Raised when a raw filing key does not match the project partition layout."""


class S3CuratedDocumentPipeline:
    """Reads immutable raw filings from S3 and writes structured JSON to S3."""

    def __init__(
        self,
        s3_client: Any,
        raw_bucket: str,
        curated_bucket: str,
        parser: SecHtmlDocumentParser | None = None,
    ) -> None:
        self._s3 = s3_client
        self.raw_bucket = raw_bucket
        self.curated_bucket = curated_bucket
        self._parser = parser or SecHtmlDocumentParser()

    @staticmethod
    def identity_from_key(key: str, metadata: dict[str, str] | None = None) -> FilingIdentity:
        match = _KEY_RE.match(key)
        if match is None:
            raise InvalidRawFilingKeyError(
                "Raw filing key must follow filings/cik=.../form=.../filing_date=.../"
                "accession=.../filename.htm."
            )
        values = match.groupdict()
        object_metadata = metadata or {}
        return FilingIdentity(
            cik=object_metadata.get("cik", values["cik"]),
            accession_number=object_metadata.get("accession-number", values["accession"]),
            form=object_metadata.get("form", values["form"]).upper(),
            filing_date=values["filing_date"],
            primary_document=values["filename"],
            company_name=object_metadata.get("company-name"),
        )

    @staticmethod
    def curated_key_for(raw_key: str) -> str:
        match = _KEY_RE.match(raw_key)
        if match is None:
            raise InvalidRawFilingKeyError(raw_key)
        values = match.groupdict()
        stem = PurePosixPath(values["filename"]).stem
        return (
            f"documents/cik={values['cik']}/form={values['form']}/"
            f"filing_date={values['filing_date']}/accession={values['accession']}/"
            f"{stem}.json"
        )

    def parse_key(self, raw_key: str) -> ParsingResult:
        curated_key = self.curated_key_for(raw_key)
        if self._exists(self.curated_bucket, curated_key):
            identity = self.identity_from_key(raw_key)
            return ParsingResult(
                status=ParsingStatus.ALREADY_EXISTS,
                raw_bucket=self.raw_bucket,
                raw_key=raw_key,
                curated_bucket=self.curated_bucket,
                curated_key=curated_key,
                document_id=identity.document_id,
            )

        response = self._s3.get_object(Bucket=self.raw_bucket, Key=raw_key)
        body = response["Body"].read()
        metadata = {str(key): str(value) for key, value in response.get("Metadata", {}).items()}
        source_sha256 = metadata.get("content-sha256") or sha256(body).hexdigest()
        identity = self.identity_from_key(raw_key, metadata)

        document = self._parser.parse(
            body=body,
            source_bucket=self.raw_bucket,
            source_key=raw_key,
            source_sha256=source_sha256,
            filing=identity,
        )
        encoded = document.model_dump_json(indent=2).encode("utf-8")

        try:
            self._s3.put_object(
                Bucket=self.curated_bucket,
                Key=curated_key,
                Body=encoded,
                ContentType="application/json",
                Metadata={
                    "document-id": identity.document_id,
                    "source-sha256": source_sha256,
                    "source-key-sha256": sha256(raw_key.encode("utf-8")).hexdigest(),
                    "parser-version": document.parser_version,
                    "form": identity.form,
                    "cik": identity.cik,
                    "accession-number": identity.accession_number,
                },
                IfNoneMatch="*",
            )
            status = ParsingStatus.STORED
        except ClientError as exc:
            status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            error_code = exc.response.get("Error", {}).get("Code")
            if status_code == 412 or error_code in {
                "PreconditionFailed",
                "ConditionalRequestConflict",
            }:
                status = ParsingStatus.ALREADY_EXISTS
            else:
                raise

        return ParsingResult(
            status=status,
            raw_bucket=self.raw_bucket,
            raw_key=raw_key,
            curated_bucket=self.curated_bucket,
            curated_key=curated_key,
            document_id=identity.document_id,
            block_count=document.diagnostics.block_count,
            section_count=document.diagnostics.section_count,
            warning_count=len(document.diagnostics.warnings),
        )

    def parse_batch(self, prefix: str = "filings/", maximum: int = 5) -> list[ParsingResult]:
        if maximum < 1:
            raise ValueError("maximum must be positive.")
        results: list[ParsingResult] = []
        paginator = self._s3.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=self.raw_bucket, Prefix=prefix):
            for item in page.get("Contents", []):
                key = str(item["Key"])
                if key.endswith(".receipt.json") or key.endswith("/"):
                    continue
                try:
                    result = self.parse_key(key)
                except InvalidRawFilingKeyError:
                    continue
                results.append(result)
                if len(results) >= maximum:
                    return results
        return results

    def read_curated_json(self, key: str) -> dict[str, Any]:
        response = self._s3.get_object(Bucket=self.curated_bucket, Key=key)
        payload = json.loads(response["Body"].read())
        if not isinstance(payload, dict):
            raise TypeError("Curated document must be a JSON object.")
        return payload

    def _exists(self, bucket: str, key: str) -> bool:
        try:
            self._s3.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as exc:
            status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            error_code = exc.response.get("Error", {}).get("Code")
            if status_code == 404 or error_code in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise
