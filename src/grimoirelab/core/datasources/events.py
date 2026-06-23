import datetime

from opensearchpy import Search

from ..config import settings
from ..utils.opensearch import get_opensearch_client


def get_events(
    sources: list = None,
    event_type: str = None,
    from_date: datetime.datetime = None,
    to_date: datetime.datetime = None,
    page: int = 1,
    size: int = 25,
) -> list:
    """
    Retrieve events from OpenSearch with optional filtering and pagination.

    :param sources: List of repository sources to filter by.
    :param event_type: Type of event to filter by.
    :param from_date: Start date for filtering events.
    :param to_date: End date for filtering events.
    :param page: Page number for pagination.
    :param size: Number of events per page.
    :return: OpenSearch response object containing the events.
    """
    opensearch = get_opensearch_client()

    index = settings.GRIMOIRELAB_ARCHIVIST["STORAGE_INDEX"]
    s = Search(using=opensearch, index=index)
    s = s.sort({"time": {"order": "asc"}}, {"id": {"order": "asc"}})

    if sources:
        s = s.filter("terms", source=sources)

    if event_type:
        s = s.filter("term", type=event_type)

    if from_date or to_date:
        range_filter = {}
        if from_date:
            range_filter["gte"] = from_date
        if to_date:
            range_filter["lte"] = to_date
        s = s.filter("range", time=range_filter)

    s = s[(page - 1) * size : page * size]

    response = s.execute()

    return response
