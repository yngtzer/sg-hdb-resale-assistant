import duckdb, sys, pathlib
import pandas as pd

DATA_CSV = pathlib.Path("data/resale-flat-prices.csv")
DB_PATH  = pathlib.Path("db/resale.duckdb")

def main():
    if len(sys.argv) > 1:
        csv_path = pathlib.Path(sys.argv[1])
    else:
        csv_path = DATA_CSV
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}. Place the dataset under data/.")

    # Load CSV with pandas for light cleanup
    df = pd.read_csv(csv_path)

    # Basic normalization
    # - Convert 'month' like '2024-06' into first-day-of-month date
    # - Coerce numeric types
    df["month"] = pd.to_datetime(df["month"].astype(str) + "-01")
    df["resale_price"] = pd.to_numeric(df["resale_price"], errors="coerce")
    df["floor_area_sqm"] = pd.to_numeric(df["floor_area_sqm"], errors="coerce")

    # Create DB and load table
    con = duckdb.connect(DB_PATH.as_posix())
    con.execute("""
        CREATE TABLE IF NOT EXISTS resale_txn (
          month DATE,
          town TEXT,
          block TEXT,
          street_name TEXT,
          flat_type TEXT,
          storey_range TEXT,
          floor_area_sqm DOUBLE,
          lease_commence_date INTEGER,
          remaining_lease TEXT,
          resale_price DOUBLE
        );
    """)
    con.execute("DELETE FROM resale_txn;")  # full refresh
    con.register("df_in", df)
    con.execute("""
        INSERT INTO resale_txn
        SELECT month, town, block, street_name, flat_type, storey_range,
               floor_area_sqm, lease_commence_date, remaining_lease, resale_price
        FROM df_in;
    """)
    con.unregister("df_in")

    # Helpful indices (DuckDB uses zone maps; these are pragmas)
    # But we can add projections and views if needed later.

    print(f"Loaded {con.execute('SELECT COUNT(*) FROM resale_txn').fetchone()[0]} rows into {DB_PATH}")

if __name__ == "__main__":
    main()
