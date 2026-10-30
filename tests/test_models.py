"""Tests for models.py: defensive parsing of string-vs-list Gamma fields."""

from __future__ import annotations

from custom_components.polymarket_watch.models import Market, Outcome, parse_json_field


def test_parse_json_field_handles_json_string() -> None:
    assert parse_json_field('["Yes", "No"]') == ["Yes", "No"]


def test_parse_json_field_handles_actual_list() -> None:
    assert parse_json_field(["Yes", "No"]) == ["Yes", "No"]


def test_parse_json_field_handles_invalid_json_string() -> None:
    assert parse_json_field("not json") == []


def test_parse_json_field_handles_none() -> None:
    assert parse_json_field(None) == []


def test_parse_json_field_handles_json_object_string() -> None:
    assert parse_json_field('{"a": 1}') == []


def test_market_from_gamma_with_string_encoded_fields() -> None:
    data = {
        "id": "123",
        "slug": "will-x-happen",
        "question": "Will X happen?",
        "conditionId": "0xabc",
        "active": True,
        "closed": False,
        "acceptingOrders": True,
        "endDate": "2026-12-31T00:00:00Z",
        "volumeNum": "1000.5",
        "volume24hr": "100.25",
        "liquidityNum": "500.0",
        "closedTime": None,
        "umaResolutionStatus": None,
        "outcomes": '["Yes", "No"]',
        "outcomePrices": '["0.6", "0.4"]',
        "clobTokenIds": '["111", "222"]',
    }
    market = Market.from_gamma(data)

    assert market.slug == "will-x-happen"
    assert market.volume == 1000.5
    assert len(market.outcomes) == 2
    assert market.outcomes[0] == Outcome(name="Yes", token_id="111", price=0.6)
    assert market.outcomes[1] == Outcome(name="No", token_id="222", price=0.4)
    assert market.end_date is not None
    assert market.end_date.year == 2026


def test_market_from_gamma_with_actual_list_fields() -> None:
    data = {
        "id": "1",
        "slug": "s",
        "question": "Q?",
        "conditionId": "c",
        "active": True,
        "closed": False,
        "acceptingOrders": True,
        "endDate": None,
        "volumeNum": 10,
        "volume24hr": 1,
        "liquidityNum": 2,
        "closedTime": None,
        "umaResolutionStatus": None,
        "outcomes": ["Yes", "No"],
        "outcomePrices": [0.3, 0.7],
        "clobTokenIds": ["a", "b"],
    }
    market = Market.from_gamma(data)

    assert [o.name for o in market.outcomes] == ["Yes", "No"]
    assert [o.token_id for o in market.outcomes] == ["a", "b"]
    assert [o.price for o in market.outcomes] == [0.3, 0.7]


def test_market_from_gamma_mismatched_lengths_does_not_crash() -> None:
    data = {
        "id": "1",
        "slug": "s",
        "question": "Q?",
        "conditionId": "c",
        "active": True,
        "closed": False,
        "acceptingOrders": True,
        "endDate": None,
        "volumeNum": 0,
        "volume24hr": 0,
        "liquidityNum": 0,
        "closedTime": None,
        "umaResolutionStatus": None,
        "outcomes": '["Yes", "No", "Maybe"]',
        "outcomePrices": '["0.5", "0.5"]',
        "clobTokenIds": "[]",
    }
    market = Market.from_gamma(data)

    assert len(market.outcomes) == 3
    assert market.outcomes[2].token_id == ""
    assert market.outcomes[2].price is None
