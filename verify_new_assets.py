import duckdb

conn = duckdb.connect('data/quant.duckdb')
rows = conn.execute("""
    SELECT symbol, timestamp, close, source, asset_class 
    FROM realtime_candles 
    WHERE symbol IN ('SOL/USD', 'NVDA') 
    ORDER BY timestamp DESC 
    LIMIT 10
""").fetchall()

print(f"{'Symbol':<10} | {'Price':<10} | {'Source':<12} | {'Class':<10}")
print("-" * 50)
for row in rows:
    sym, ts, c, src, cls = row
    print(f"{sym:<10} | {c:<10.2f} | {src:<12} | {cls:<10}")

conn.close()
