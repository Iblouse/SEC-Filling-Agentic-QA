"""SEC filing HTML parsing and curated-document storage."""

from edgar_qa.parsing.html_parser import SecHtmlDocumentParser
from edgar_qa.parsing.pipeline import S3CuratedDocumentPipeline

__all__ = ["S3CuratedDocumentPipeline", "SecHtmlDocumentParser"]
