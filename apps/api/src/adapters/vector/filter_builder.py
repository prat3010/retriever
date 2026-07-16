from collections.abc import Callable
from typing import Any

from src.domain.abstractions.retrieval import MetadataFilter, SearchResult

_OP_TO_SQL: dict[str, tuple[str, Callable[[Any], Any]]] = {
    "eq":       ("{alias}.meta_data ->> '{field}' = :{param}", str),
    "neq":      ("{alias}.meta_data ->> '{field}' != :{param}", str),
    "in":       ("{alias}.meta_data -> '{field}' ?| :{param}", lambda v: [str(x) for x in (v or [])]),
    "gt":       ("({alias}.meta_data ->> '{field}')::numeric > :{param}", str),
    "gte":      ("({alias}.meta_data ->> '{field}')::numeric >= :{param}", str),
    "lt":       ("({alias}.meta_data ->> '{field}')::numeric < :{param}", str),
    "lte":      ("({alias}.meta_data ->> '{field}')::numeric <= :{param}", str),
    "contains": ("{alias}.meta_data @> :{param}::jsonb", lambda v: v),
    "regex":    ("{alias}.meta_data ->> '{field}' ~* :{param}", str),
}


def rows_to_search_results(rows: list[Any]) -> list[SearchResult]:
    return [
        SearchResult(
            chunk_id=str(row[0]),
            document_id=str(row[1]),
            content=row[2],
            score=float(row[4]),
            metadata=row[3] if isinstance(row[3], dict) else {},
        )
        for row in rows
    ]


def build_filter_clause(
    filters: list[MetadataFilter],
    tags: list[str],
    chunk_alias: str = "dc",
) -> tuple[str, dict[str, Any], str]:
    """Build SQL filter clause, params, and optional JOIN for search queries.

    Returns (where_clause_sql, params_dict, join_clause_sql).
    """
    conditions: list[str] = []
    params: dict[str, Any] = {}
    join_clause = ""

    if tags:
        join_clause = f" JOIN documents d ON {chunk_alias}.document_id = d.document_id"
        conditions.append("d.tags @> ARRAY[:tag_filters]::varchar[]")
        params["tag_filters"] = tags

    for i, f in enumerate(filters):
        p = f"f_{i}"
        if f.operator == "exists":
            conditions.append(f"{chunk_alias}.meta_data ? :{p}")
            params[p] = f.field
            continue
        sql_tpl, prepare = _OP_TO_SQL[f.operator]
        conditions.append(sql_tpl.format(alias=chunk_alias, field=f.field, param=p))
        params[p] = prepare(f.value)

    if conditions:
        return " AND " + " AND ".join(conditions), params, join_clause

    return "", params, join_clause
