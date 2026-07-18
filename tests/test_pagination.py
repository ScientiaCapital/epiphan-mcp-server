"""Tests for integrations/_pagination.py's shared extract_page helper."""

from epiphan_mcp.integrations._pagination import extract_page


class TestExtractPageItems:
    def test_prefers_results_key(self):
        items, _ = extract_page({"results": [{"id": 1}], "data": [{"id": 2}]})
        assert items == [{"id": 1}]

    def test_falls_back_to_data_key(self):
        items, _ = extract_page({"data": [{"id": 2}]})
        assert items == [{"id": 2}]

    def test_falls_back_to_platform_specific_key(self):
        items, _ = extract_page({"Results": [{"id": 3}]}, "Results")
        assert items == [{"id": 3}]

    def test_no_matching_key_returns_empty(self):
        items, truncated = extract_page({"unrelated": "value"})
        assert items == []
        assert truncated is False

    def test_non_list_value_at_key_is_ignored(self):
        items, _ = extract_page({"results": "not-a-list", "data": [{"id": 4}]})
        assert items == [{"id": 4}]


class TestExtractPageTruncation:
    def test_next_link_present_means_truncated(self):
        _, truncated = extract_page({"results": [], "next": "https://example.com/page2"})
        assert truncated is True

    def test_next_token_present_means_truncated(self):
        _, truncated = extract_page({"results": [], "nextToken": "abc123"})
        assert truncated is True

    def test_has_more_true_means_truncated(self):
        _, truncated = extract_page({"results": [], "hasMore": True})
        assert truncated is True

    def test_has_more_false_is_not_truncated_on_its_own(self):
        _, truncated = extract_page({"results": [{"id": 1}], "hasMore": False})
        assert truncated is False

    def test_total_greater_than_page_size_means_truncated(self):
        _, truncated = extract_page({"results": [{"id": 1}], "total": 5})
        assert truncated is True

    def test_total_equal_to_page_size_is_not_truncated(self):
        _, truncated = extract_page({"results": [{"id": 1}], "total": 1})
        assert truncated is False

    def test_non_int_total_is_ignored(self):
        _, truncated = extract_page({"results": [{"id": 1}], "total": "many"})
        assert truncated is False

    def test_alternate_total_keys(self):
        for key in ("totalResults", "totalCount", "TotalNumberOfResults"):
            _, truncated = extract_page({"results": [], key: 3})
            assert truncated is True, f"{key} should trigger truncation"

    def test_no_truncation_signal_returns_false(self):
        _, truncated = extract_page({"results": [{"id": 1}, {"id": 2}]})
        assert truncated is False
