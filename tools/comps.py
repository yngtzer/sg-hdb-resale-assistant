from tools.sql_utils import duckdb_conn

def sql_comps(mode="town", town=None, block=None, flat_type="4 ROOM", lookback_months=12):
    """
    mode: "town" or "block"
    returns dict with summary stats + sample recent deals
    """
    con = duckdb_conn()
    where = []
    params = []

    if flat_type:
        where.append("flat_type = ?")
        params.append(flat_type)

    if mode == "block" and block:
        where.append("block = ?")
        params.append(block)
    elif town:
        where.append("town = ?")
        params.append(town)

    # Lookback: last N months from latest month in table
    # Use max(month) as reference
    max_month = con.execute("SELECT MAX(month) FROM resale_txn").fetchone()[0]
    where.append("month >= (DATE_TRUNC('month', ?) - (? * INTERVAL '1 month'))")
    params.extend([max_month, lookback_months])

    where_sql = " AND ".join(where) if where else "1=1"

    # Summary stats (median and IQR)
    summary_sql = f"""
      WITH base AS (
        SELECT *
        FROM resale_txn
        WHERE {where_sql}
      )
      SELECT
        COUNT(*)                          AS deals,
        MIN(month)                        AS first_month,
        MAX(month)                        AS last_month,
        AVG(floor_area_sqm)               AS avg_sqm,
        MEDIAN(resale_price)              AS median_price,
        QUANTILE_CONT(resale_price, 0.25) AS p25_price,
        QUANTILE_CONT(resale_price, 0.75) AS p75_price
      FROM base
    """

    # Monthly series for charting
    series_sql = f"""
      WITH base AS (
        SELECT *
        FROM resale_txn
        WHERE {where_sql}
      )
      SELECT
        DATE_TRUNC('month', month) AS mth,
        COUNT(*)                   AS deals,
        MEDIAN(resale_price)       AS median_price
      FROM base
      GROUP BY 1
      ORDER BY 1
    """

    # Sample recent transactions
    recent_sql = f"""
      SELECT month, town, block, street_name, flat_type, storey_range,
             floor_area_sqm, resale_price,
             (resale_price / (floor_area_sqm * 10.7639)) AS psf_est
      FROM resale_txn
      WHERE {where_sql}
      ORDER BY month DESC
      LIMIT 20
    """

    # DuckDB param names must exist in dict; map positional params
    # We'll pass positional for the date filters
    params_list = []
    # Build params for the date filter used twice (summary/series/recent)
    def bind_params(base_params):
        local = []
        for k,v in base_params.items():
            if k in ("_max_month","_lookback"): continue
            local.append(v)
        # append positional date params
        local.append(params["_max_month"])
        local.append(params["_lookback"])
        return tuple(local)

    # Order of named params must match usage; simpler: expand to positional
    # Build a base-params tuple for each query
    # Extract in the same order as in where_sql
    def ordered_values():
        order = []
        if "flat_type = :flat_type" in where_sql: order.append(params["flat_type"])
        if "block = :block" in where_sql: order.append(params.get("block"))
        if "town = :town" in where_sql: order.append(params.get("town"))
        return order

    base_vals = ordered_values()
    summary = con.execute(summary_sql, params).fetchone()
    series  = con.execute(series_sql,  params).fetchall()
    recent  = con.execute(recent_sql,  params).fetchall()

    summary_cols = ["deals","first_month","last_month","avg_sqm","median_price","p25_price","p75_price"]
    series_cols  = ["month","deals","median_price"]
    recent_cols  = ["month","town","block","street_name","flat_type","storey_range","floor_area_sqm","resale_price","psf_est"]

    # Convert to dicts
    def rows_to_dicts(rows, cols):
        return [dict(zip(cols, r)) for r in rows]

    return {
        "summary": dict(zip(summary_cols, summary)) if summary else {},
        "series": rows_to_dicts(series, series_cols),
        "recent": rows_to_dicts(recent, recent_cols)
    }
