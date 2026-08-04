from __future__ import annotations

from unittest.mock import Mock

import pytest

from database.models import SourceConfig
from sources.x_monitor import XMonitor


def source(*, username: str = "expected_user", query: str = "") -> SourceConfig:
    return SourceConfig(
        id="expected-user-x",
        person_id="expected_user",
        platform="X",
        source_type="x_api",
        source_confidence=0.96,
        speaker_confidence=0.99,
        extra={"username": username, "query": query, "person_name": "Expected User"},
    )


def test_default_query_is_author_scoped_and_excludes_retweets():
    monitor = XMonitor(source(), "token")

    assert monitor._validated_query() == "from:expected_user -is:retweet"


@pytest.mark.parametrize(
    "query",
    [
        "Nvidia OR NVDA -is:retweet",
        "from:someone_else Nvidia -is:retweet",
        "from:expected_user OR from:someone_else Nvidia -is:retweet",
        "from:expected_user Nvidia",
    ],
)
def test_custom_query_must_remain_author_scoped_and_exclude_retweets(query):
    monitor = XMonitor(source(query=query), "token")

    with pytest.raises(ValueError, match="X query must"):
        monitor._validated_query()


def test_retweet_response_is_discarded_even_with_safe_query(monkeypatch):
    response = Mock(status_code=200)
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "data": [
            {
                "id": "1",
                "text": "Nvidia is amazing",
                "referenced_tweets": [{"type": "retweeted", "id": "original"}],
            },
            {"id": "2", "text": "Nvidia is amazing", "referenced_tweets": []},
        ]
    }
    request = Mock(return_value=response)
    monkeypatch.setattr("sources.x_monitor.requests.get", request)
    monitor = XMonitor(source(query="from:expected_user Nvidia -is:retweet"), "token")

    statements = monitor.fetch()

    assert [statement.platform_item_id for statement in statements] == ["2"]
    assert request.call_args.kwargs["params"]["query"] == "from:expected_user Nvidia -is:retweet"
