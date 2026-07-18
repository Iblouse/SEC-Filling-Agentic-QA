from datetime import date, datetime
from hashlib import sha256

from pydantic import BaseModel, Field, HttpUrl, field_validator


class FilingMetadata(BaseModel):
    """Normalized filing metadata from the SEC submissions endpoint."""

    cik: str
    company_name: str
    accession_number: str
    form: str
    filing_date: date
    report_date: date | None = None
    primary_document: str
    source_url: HttpUrl
    is_inline_xbrl: bool = False
    file_number: str | None = None
    film_number: str | None = None

    @field_validator("cik")
    @classmethod
    def normalize_cik(cls, value: str) -> str:
        digits = "".join(character for character in value if character.isdigit())
        if not digits:
            raise ValueError("CIK must contain digits.")
        return digits.zfill(10)

    @property
    def accession_number_compact(self) -> str:
        return self.accession_number.replace("-", "")

    @property
    def deterministic_id(self) -> str:
        identity = f"{self.cik}:{self.accession_number}:{self.primary_document}"
        return sha256(identity.encode("utf-8")).hexdigest()

    @property
    def raw_document_key(self) -> str:
        safe_form = self.form.lower().replace("/", "-")
        return (
            f"filings/cik={self.cik}/form={safe_form}/"
            f"filing_date={self.filing_date.isoformat()}/"
            f"accession={self.accession_number_compact}/{self.primary_document}"
        )


class FilingManifest(BaseModel):
    """A versionable manifest for a set of SEC filings."""

    cik: str
    company_name: str
    filings: list[FilingMetadata] = Field(default_factory=list)


class FilingIngestionJob(BaseModel):
    """At-least-once queue message for downloading one SEC filing document."""

    schema_version: str = "1.0"
    job_id: str
    discovered_at: datetime
    filing: FilingMetadata
    destination_bucket: str
    destination_key: str

    @classmethod
    def from_filing(
        cls,
        filing: FilingMetadata,
        destination_bucket: str,
        discovered_at: datetime,
    ) -> "FilingIngestionJob":
        return cls(
            job_id=filing.deterministic_id,
            discovered_at=discovered_at,
            filing=filing,
            destination_bucket=destination_bucket,
            destination_key=filing.raw_document_key,
        )
