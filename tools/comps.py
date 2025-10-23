from tools.sql_utils import duckdb_conn

SQM_TO_SQFT = 10.7639

def sql_comps(mode="town", town=None, block=None, flat_type="4 ROOM", lookback_months=12):
    """
    mode: "town" or "block"
    returns dict with summary stats + monthly series + recent comps (with PSF)
    """
    con = duckdb_conn()
    filters = []
    vals = []

    if flat_type:
        filters.append("flat_type = ?")
        vals.append(flat_type)

    if mode == "block" and block:
        filters.append("block = ?")
        vals.append(block)
    elif town:
        filters.append("town = ?")
        vals.append(town)

    # Reference month for lookback
    max_month = con.execute("SELECT MAX(month) FROM resale_txn").fetchone()[0]
    filters.append("month >= (date_trunc('month', ?) - (? * INTERVAL '1' MONTH))")
    vals.extend([max_month, lookback_months])

    where_sql = " AND ".join(filters) if filters else "1=1"

    # Summary: include PSF percentiles (derived)
    summary_sql = f"""
      WITH base AS (
        SELECT *,
               (resale_price / (floor_area_sqm * {SQM_TO_SQFT})) AS psf
        FROM resale_txn
        WHERE {where_sql}
      )
      SELECT
        COUNT(*)                                  AS deals,
        MIN(month)                                AS first_month,
        MAX(month)                                AS last_month,
        MEDIAN(resale_price)                      AS median_price,
        QUANTILE_CONT(resale_price, 0.25)         AS p25_price,
        QUANTILE_CONT(resale_price, 0.75)         AS p75_price,
        MEDIAN(psf)                               AS median_psf,
        QUANTILE_CONT(psf, 0.25)                  AS p25_psf,
        QUANTILE_CONT(psf, 0.75)                  AS p75_psf,
        AVG(floor_area_sqm)                       AS avg_sqm
      FROM base
    """

    # Monthly median series (price + PSF) for charting
    series_sql = f"""
      WITH base AS (
        SELECT DATE_TRUNC('month', month) AS mth,
               resale_price,
               (resale_price / (floor_area_sqm * {SQM_TO_SQFT})) AS psf
        FROM resale_txn
        WHERE {where_sql}
      )
      SELECT
        mth,
        COUNT(*)                     AS deals,
        MEDIAN(resale_price)         AS median_price,
        MEDIAN(psf)                  AS median_psf
      FROM base
      GROUP BY 1
      ORDER BY 1
    """

    # Recent comps (20 latest)
    recent_sql = f"""
      SELECT month, town, block, street_name, flat_type, storey_range,
             floor_area_sqm,
             resale_price,
             (resale_price / (floor_area_sqm * {SQM_TO_SQFT})) AS psf
      FROM resale_txn
      WHERE {where_sql}
      ORDER BY month DESC
      LIMIT 20
    """

    summary = con.execute(summary_sql, tuple(vals)).fetchone()
    series  = con.execute(series_sql,  tuple(vals)).fetchall()
    recent  = con.execute(recent_sql,  tuple(vals)).fetchall()

    summary_cols = [
        "deals","first_month","last_month","median_price","p25_price","p75_price",
        "median_psf","p25_psf","p75_psf","avg_sqm"
    ]
    series_cols  = ["month","deals","median_price","median_psf"]
    recent_cols  = ["month","town","block","street_name","flat_type","storey_range",
                    "floor_area_sqm","resale_price","psf"]

    def rows_to_dicts(rows, cols):
        return [dict(zip(cols, r)) for r in rows]

    return {
        "summary": dict(zip(summary_cols, summary)) if summary else {},
        "series": rows_to_dicts(series, series_cols),
        "recent": rows_to_dicts(recent, recent_cols),
        "params": {"mode": mode, "town": town, "block": block, "flat_type": flat_type, "lookback_months": lookback_months}
    }
