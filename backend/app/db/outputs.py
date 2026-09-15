"""Persist derived tables in the agent session's transaction."""

from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.db.database import Base


def replace_output(
    db: Session,
    table_name: str,
    rows: pd.DataFrame | Iterable[Mapping[str, Any]],
) -> None:
    """Replace rows without dropping constraints or committing a partial result.

    BaseAgent commits the output and audit record together after validation.
    Using the session connection also keeps multi-table agent writes atomic.
    """
    table = Base.metadata.tables[table_name]
    db.execute(table.delete())
    if isinstance(rows, pd.DataFrame):
        rows.to_sql(table_name, db.connection(), if_exists="append", index=False)
    else:
        records = list(rows)
        if records:
            db.execute(table.insert(), records)
