from __future__ import annotations

from trump_market_alert.config import Settings
from trump_market_alert.db import Database


def main() -> int:
    s = Settings.load()
    db = Database(s.database_url, s.root_dir)
    db.connect()
    try:
        cur = db.execute("SELECT sent_at, signal, confidence, source_platform, quote FROM alerts ORDER BY id DESC LIMIT 20")
        rows = cur.fetchall()
        for row in rows:
            vals = list(row) if db.kind == "postgres" else [row[k] for k in row.keys()]
            print(" | ".join(str(x).replace("\n", " ")[:120] for x in vals))
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
