"""Raw-layer extraction for the Taiwan CDC disease project.

Downloads the source CSVs from the CDC open-data host and lands them, unchanged,
as timestamped Parquet files under data/raw/<dataset>/. The raw layer preserves
the original columns verbatim (only lineage columns prefixed with `_` are added)
so the files stay faithful to the source for debugging and reprocessing.

Run:  python src/extract_raw.py
"""
from __future__ import annotations

import io
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import certifi
import pandas as pd
import requests

# Project layout: this file is at <root>/src/extract_raw.py
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"            # timestamped history (gitignored, local)
SNAPSHOT_DIR = ROOT / "data" / "snapshot"  # stable latest per dataset (committed)
# The CDC host firewalls non-Taiwan / cloud IPs, so GitHub Actions runners cannot
# fetch it. Extraction therefore runs from a Taiwan-networked machine and commits
# the snapshot; CI/CD builds & deploys from the committed snapshot (no network).
# CDC's server omits the TWCA intermediate cert. Windows/macOS complete the chain
# via AIA fetching, but Linux/OpenSSL (GitHub Actions) does not — so we ship the
# intermediate and splice it into the CA bundle. This works on every platform and
# needs no OS-specific behaviour.
INTERMEDIATE_PEM = ROOT / "certs" / "twca_ssl_intermediate.pem"


def ca_bundle() -> str:
    """certifi roots + the bundled CDC intermediate, written to one temp PEM."""
    if not INTERMEDIATE_PEM.exists():
        return certifi.where()   # fall back to default roots
    tmp = tempfile.NamedTemporaryFile(
        "w", suffix="_cdc_ca.pem", delete=False, encoding="utf-8")
    tmp.write(Path(certifi.where()).read_text(encoding="utf-8"))
    tmp.write("\n")
    tmp.write(INTERMEDIATE_PEM.read_text(encoding="utf-8"))
    tmp.close()
    return tmp.name

# One source CSV per dataset. `url` is the stable direct-download endpoint.
SOURCES: list[dict] = [
    {
        "name": "nhi_influenza_like_illness",
        "disease": "流感",
        "url": "https://od.cdc.gov.tw/eic/NHI_Influenza_like_illness.csv",
        "grain": "weekly x county x age",
    },
    {
        "name": "nhi_enteroviral_infection",
        "disease": "腸病毒",
        "url": "https://od.cdc.gov.tw/eic/NHI_EnteroviralInfection.csv",
        "grain": "weekly x county x age",
    },
    {
        "name": "covid_age_county_gender",
        "disease": "COVID-19",
        "url": "https://od.cdc.gov.tw/eic/Age_County_Gender_19CoV.csv",
        "grain": "monthly x county/town x gender x age",
    },
    {
        "name": "dengue_daily",
        "disease": "登革熱",
        # Full historical line-list (not the rolling _last12m window).
        "url": "https://od.cdc.gov.tw/eic/Dengue_Daily.csv",
        "fallback_url": "https://od.cdc.gov.tw/eic/Dengue_Daily_last12m.csv",
        "grain": "per-case (daily)",
    },
]

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "tw-disease-data/1.0 (portfolio ETL)"})
SESSION.verify = ca_bundle()


def fetch_csv(url: str) -> pd.DataFrame:
    resp = SESSION.get(url, timeout=120)
    resp.raise_for_status()
    # CDC CSVs are UTF-8, frequently with a BOM. Keep everything as string in the
    # raw layer so no implicit type coercion happens before the ETL stage.
    text = resp.content.decode("utf-8-sig", errors="replace")
    return pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)


def land(source: dict, ingested_at: datetime) -> dict:
    url = source["url"]
    try:
        df = fetch_csv(url)
    except Exception as exc:
        fallback = source.get("fallback_url")
        if not fallback:
            raise
        print(f"[warn] {source['name']}: primary failed ({exc!r}); using fallback")
        url = fallback
        df = fetch_csv(url)

    # Lineage columns (prefixed so they never collide with source columns).
    df["_source_url"] = url
    df["_ingested_at"] = ingested_at.isoformat()

    ts = ingested_at.strftime("%Y%m%dT%H%M%SZ")
    out_dir = RAW_DIR / source["name"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{source['name']}_{ts}.parquet"
    df.to_parquet(out_path, engine="pyarrow", index=False, compression="snappy")

    # Stable committed snapshot the warehouse build reads (network-independent CI).
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(SNAPSHOT_DIR / f"{source['name']}.parquet",
                  engine="pyarrow", index=False, compression="snappy")

    return {
        "name": source["name"],
        "disease": source["disease"],
        "rows": len(df),
        "cols": df.shape[1],
        "source_url": url,
        "path": str(out_path.relative_to(ROOT)),
    }


def main() -> int:
    ingested_at = datetime.now(timezone.utc)
    print(f"Raw ingest @ {ingested_at.isoformat()}\n")
    results, failed = [], []
    for source in SOURCES:
        try:
            info = land(source, ingested_at)
            results.append(info)
            print(f"[ OK ] {info['name']:<28} rows={info['rows']:>7} "
                  f"cols={info['cols']:>2}  -> {info['path']}")
        except Exception as exc:
            failed.append(source["name"])
            print(f"[FAIL] {source['name']:<28} {exc!r}")

    print(f"\nLanded {len(results)}/{len(SOURCES)} datasets under {RAW_DIR.relative_to(ROOT)}/")
    # Non-zero exit on any failure so CI (GitHub Actions) fails loudly.
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
