"""Tests for M18: Metadata & Tag Filtering."""


from src.adapters.vector.filter_builder import build_filter_clause
from src.domain.abstractions.retrieval import MetadataFilter

# --- filter_builder unit tests ---


def test_no_filters_or_tags() -> None:
    sql, params, join = build_filter_clause([], [])
    assert sql == ""
    assert params == {}
    assert join == ""


def test_tag_filter() -> None:
    sql, params, join = build_filter_clause([], ["finance", "quarterly"])
    assert "JOIN documents d ON" in join
    assert "d.tags @> ARRAY[:tag_filters]::varchar[]" in sql
    assert params["tag_filters"] == ["finance", "quarterly"]


def test_eq_filter() -> None:
    flt = [MetadataFilter(field="department", operator="eq", value="legal")]
    sql, params, _ = build_filter_clause(flt, [])
    assert "dc.meta_data ->> 'department' = :f_0" in sql
    assert params["f_0"] == "legal"


def test_neq_filter() -> None:
    flt = [MetadataFilter(field="status", operator="neq", value="archived")]
    sql, params, _ = build_filter_clause(flt, [])
    assert "dc.meta_data ->> 'status' != :f_0" in sql
    assert params["f_0"] == "archived"


def test_in_filter() -> None:
    flt = [MetadataFilter(field="category", operator="in", value=["a", "b"])]
    sql, params, _ = build_filter_clause(flt, [])
    assert "dc.meta_data -> 'category' ?| :f_0" in sql
    assert params["f_0"] == ["a", "b"]


def test_gt_filter() -> None:
    flt = [MetadataFilter(field="year", operator="gt", value=2025)]
    sql, params, _ = build_filter_clause(flt, [])
    assert "(dc.meta_data ->> 'year')::numeric > :f_0" in sql
    assert params["f_0"] == "2025"


def test_gte_filter() -> None:
    flt = [MetadataFilter(field="year", operator="gte", value=2020)]
    sql, _, _ = build_filter_clause(flt, [])
    assert ">= :f_0" in sql


def test_lt_filter() -> None:
    flt = [MetadataFilter(field="amount", operator="lt", value=1000)]
    sql, _, _ = build_filter_clause(flt, [])
    assert "< :f_0" in sql


def test_lte_filter() -> None:
    flt = [MetadataFilter(field="amount", operator="lte", value=500)]
    sql, _, _ = build_filter_clause(flt, [])
    assert "<= :f_0" in sql


def test_exists_filter() -> None:
    flt = [MetadataFilter(field="case_number", operator="exists", value=None)]
    sql, params, _ = build_filter_clause(flt, [])
    assert "dc.meta_data ? :f_0" in sql
    assert params["f_0"] == "case_number"


def test_contains_filter() -> None:
    flt = [MetadataFilter(field="metadata", operator="contains", value='{"key": "val"}')]
    sql, params, _ = build_filter_clause(flt, [])
    assert "dc.meta_data @> :f_0::jsonb" in sql
    assert params["f_0"] == '{"key": "val"}'


def test_regex_filter() -> None:
    flt = [MetadataFilter(field="filename", operator="regex", value="^2024.*")]
    sql, params, _ = build_filter_clause(flt, [])
    assert "~* :f_0" in sql
    assert params["f_0"] == "^2024.*"


def test_multiple_filters_anded() -> None:
    flt = [
        MetadataFilter(field="department", operator="eq", value="legal"),
        MetadataFilter(field="year", operator="gte", value=2024),
    ]
    sql, params, _ = build_filter_clause(flt, [])
    assert "AND" in sql
    assert "f_0" in params
    assert "f_1" in params


def test_tags_and_filters_combined() -> None:
    flt = [MetadataFilter(field="status", operator="eq", value="active")]
    sql, params, join = build_filter_clause(flt, ["hr"])
    assert join
    assert "d.tags @> ARRAY[:tag_filters]::varchar[]" in sql
    assert "dc.meta_data ->> 'status' = :f_0" in sql
    assert params["f_0"] == "active"
    assert params["tag_filters"] == ["hr"]


# --- SearchQuery with filters ---


def test_search_query_accepts_typed_filters() -> None:
    from src.domain.abstractions.retrieval import SearchQuery

    flt = [MetadataFilter(field="dept", operator="eq", value="eng")]
    q = SearchQuery(query="test", tenant_id="t1", filters=flt, tags=["prod"])
    assert q.filters == flt
    assert q.tags == ["prod"]


def test_search_query_defaults() -> None:
    from src.domain.abstractions.retrieval import SearchQuery

    q = SearchQuery(query="test", tenant_id="t1")
    assert q.filters == []
    assert q.tags == []


# --- Document domain model with tags ---


def test_document_with_tags() -> None:
    from src.domain.abstractions.ingestion import Document

    doc = Document(
        document_id="d1",
        tenant_id="t1",
        filename="r.pdf",
        file_hash="abc",
        storage_path="/tmp/r.pdf",
        file_size=100,
        mime_type="application/pdf",
        status="INDEXED",
        tags=["finance", "quarterly"],
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
    )
    assert doc.tags == ["finance", "quarterly"]


def test_document_tags_default() -> None:
    from src.domain.abstractions.ingestion import Document

    doc = Document(
        document_id="d2",
        tenant_id="t1",
        filename="a.txt",
        file_hash="def",
        storage_path="/tmp/a.txt",
        file_size=50,
        mime_type="text/plain",
        status="PENDING",
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
    )
    assert doc.tags == []
