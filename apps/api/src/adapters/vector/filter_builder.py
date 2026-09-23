import re
from collections.abc import Callable
from typing import Any

from src.domain.abstractions.exceptions import InvalidFilterError
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

# Metadata field names are interpolated into SQL templates verbatim, so only
# allow conservative identifier characters to prevent SQL injection.
_FIELD_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")


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
    filters: list[MetadataFilter] | dict[str, Any] | None = None,
    tags: list[str] | None = None,
    chunk_alias: str = "dc",
    collection_id: str | None = None,
    user_id: str | None = None,
    user_role: str | None = None,
    user_groups: list[str] | None = None,
    enable_acl_filter: bool = True,
) -> tuple[str, dict[str, Any], str]:
    """Build SQL filter clause, params, and optional JOIN for search queries.

    Returns (where_clause_sql, params_dict, join_clause_sql).
    """
    conditions: list[str] = []
    params: dict[str, Any] = {}
    join_clause = ""

    if collection_id:
        conditions.append(f"{chunk_alias}.collection_id = CAST(:collection_id AS uuid)")
        params["collection_id"] = str(collection_id)

    if tags:
        join_clause = f" JOIN documents d ON {chunk_alias}.document_id = d.document_id"
        conditions.append("d.tags @> ARRAY[:tag_filters]::varchar[]")
        params["tag_filters"] = tags

    # Chunk-level Access Control List (ACL) inheritance enforcement
    # Admin users bypass chunk ACL restrictions within their tenant boundary
    if enable_acl_filter and user_role != "admin":
        acl_or_clauses: list[str] = [
            f"({chunk_alias}.meta_data ->> 'is_public')::boolean = true",
            (
                f"(({chunk_alias}.meta_data -> 'allowed_users') IS NULL "
                f"AND ({chunk_alias}.meta_data -> 'allowed_groups') IS NULL "
                f"AND ({chunk_alias}.meta_data -> 'allowed_roles') IS NULL)"
            ),
        ]

        if user_id is not None:
            params["acl_user_id"] = str(user_id)
            acl_or_clauses.append(
                f"(jsonb_typeof({chunk_alias}.meta_data -> 'allowed_users') = 'array' "
                f"AND ({chunk_alias}.meta_data -> 'allowed_users') ? :acl_user_id)"
            )

        if user_role is not None:
            params["acl_user_role"] = str(user_role)
            acl_or_clauses.append(
                f"(jsonb_typeof({chunk_alias}.meta_data -> 'allowed_roles') = 'array' "
                f"AND ({chunk_alias}.meta_data -> 'allowed_roles') ? :acl_user_role)"
            )

        if user_groups:
            params["acl_user_groups"] = [str(g) for g in user_groups]
            acl_or_clauses.append(
                f"(jsonb_typeof({chunk_alias}.meta_data -> 'allowed_groups') = 'array' "
                f"AND ({chunk_alias}.meta_data -> 'allowed_groups') ?| :acl_user_groups)"
            )

        conditions.append(f"({' OR '.join(acl_or_clauses)})")

    # Normalize filters if passed as dictionary or list of MetadataFilter
    norm_filters: list[MetadataFilter] = []
    if isinstance(filters, dict):
        for k, v in filters.items():
            norm_filters.append(MetadataFilter(field=k, operator="eq", value=v))
    elif filters:
        norm_filters = list(filters)

    for i, f in enumerate(norm_filters):
        p = f"f_{i}"
        if f.operator not in _OP_TO_SQL and f.operator != "exists":
            raise InvalidFilterError(f"Unsupported metadata filter operator: {f.operator!r}")
        if not _FIELD_NAME_RE.match(f.field):
            raise InvalidFilterError(f"Invalid metadata field name: {f.field!r}")
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

