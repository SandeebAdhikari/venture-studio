"""Executive report package."""

from app.reports.executive.generator import ExecutiveReportGenerator
from app.reports.executive.service import ExecutiveReportService

__all__ = ["ExecutiveReportGenerator", "ExecutiveReportService"]
