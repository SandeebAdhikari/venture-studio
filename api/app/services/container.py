"""Service container wiring repositories to services."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.collection.service import ComplaintCollectionService
from app.repositories import RepositoryContainer, get_repositories
from app.services.category import CategoryService
from app.services.complaint import ComplaintService
from app.services.opportunity import OpportunityService
from app.services.report import ReportService
from app.services.source import SourceService


class ServiceContainer:
    def __init__(self, repos: RepositoryContainer) -> None:
        self.sources = SourceService(repos)
        self.collection = ComplaintCollectionService(repos)
        self.categories = CategoryService(repos)
        self.complaints = ComplaintService(repos)
        self.opportunities = OpportunityService(repos)
        self.reports = ReportService(repos)


def get_services(session: AsyncSession) -> ServiceContainer:
    return ServiceContainer(get_repositories(session))
