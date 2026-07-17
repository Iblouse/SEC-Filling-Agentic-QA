from datetime import date

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


class FilingManifest(BaseModel):
    """A versionable manifest for a set of SEC filings."""

    cik: str
    company_name: str
    filings: list[FilingMetadata] = Field(default_factory=list)
