from typing import Any

from src.domain.abstractions.retrieval import MetadataFilter


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
        conditions.append(f"d.tags @> ARRAY[:tag_filters]::varchar[]")
        params["tag_filters"] = tags

    for i, f in enumerate(filters):
        p = f"f_{i}"
        if f.operator == "eq":
            conditions.append(f"{chunk_alias}.meta_data ->> '{f.field}' = :{p}")
            params[p] = str(f.value)
        elif f.operator == "neq":
            conditions.append(f"{chunk_alias}.meta_data ->> '{f.field}' != :{p}")
            params[p] = str(f.value)
        elif f.operator == "in":
            conditions.append(f"{chunk_alias}.meta_data -> '{f.field}' ?| :{p}")
            params[p] = [str(v) for v in (f.value or [])]
        elif f.operator == "gt":
            conditions.append(f"({chunk_alias}.meta_data ->> '{f.field}')::numeric > :{p}")
            params[p] = str(f.value)
        elif f.operator == "gte":
            conditions.append(f"({chunk_alias}.meta_data ->> '{f.field}')::numeric >= :{p}")
            params[p] = str(f.value)
        elif f.operator == "lt":
            conditions.append(f"({chunk_alias}.meta_data ->> '{f.field}')::numeric < :{p}")
            params[p] = str(f.value)
        elif f.operator == "lte":
            conditions.append(f"({chunk_alias}.meta_data ->> '{f.field}')::numeric <= :{p}")
            params[p] = str(f.value)
        elif f.operator == "exists":
            conditions.append(f"{chunk_alias}.meta_data ? :{p}")
            params[p] = f.field
        elif f.operator == "contains":
            conditions.append(f"{chunk_alias}.meta_data @> :{p}::jsonb")
            params[p] = f.value
        elif f.operator == "regex":
            conditions.append(f"{chunk_alias}.meta_data ->> '{f.field}' ~* :{p}")
            params[p] = str(f.value)

    if conditions:
        return " AND " + " AND ".join(conditions), params, join_clause

    return "", params, join_clause
