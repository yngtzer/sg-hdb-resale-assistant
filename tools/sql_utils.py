import duckdb
from pathlib import Path

DB_PATH = Path("db/resale.duckdb")

def duckdb_conn():
    return duckdb.connect(DB_PATH.as_posix(), read_only=False)
