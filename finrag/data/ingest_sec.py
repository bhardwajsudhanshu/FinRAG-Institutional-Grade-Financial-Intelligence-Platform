"""SEC EDGAR ingestion.

Pulls 10-K filings for a list of tickers, stores raw HTML locally, and
emits a parquet manifest with metadata.

Design notes:
- We use `sec-edgar-api` for ticker → CIK mapping and filing lookup. It
  handles the EDGAR quirks (zero-padded CIKs, accession numbers, etc.).
- We respect the 10 req/sec EDGAR rate limit. `time.sleep(0.15)` is enough
  for batched pulls.
- Raw filings are stored at `data/raw/{ticker}/{filing_date}/10k.html` so
  re-ingestion is idempotent. We never re-download a filing we already have.
- The manifest `data/raw/filings.parquet` is the single source of truth for
  "what filings do we have". Downstream code reads the manifest, not the
  filesystem directly.

Sample mode (for the smoke test): one filing (AAPL FY2023 10-K) only.
Full mode: 20 tickers × 3 years.
"""

from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from loguru import logger

# Tickers covered by FinRAG (3 years, mix of sectors)
DEFAULT_TICKERS: list[str] = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META",  # mega-cap tech
    "JPM", "GS", "BAC",                                # financials
    "XOM", "CVX",                                      # energy
    "JNJ", "PFE", "UNH",                               # healthcare
    "KO", "PG", "WMT", "COST",                         # consumer staples/discretionary
    "TSLA",                                            # narrative variety
    "BRK.B",                                           # conglomerates
]

# Fallback CIK lookup — sec-edgar-api has a built-in, but this is a safety net
# so the smoke test works even if the network is flaky.
FALLBACK_CIK = {
    "AAPL": "0000320193", "MSFT": "0000789019", "GOOGL": "0001652044",
    "AMZN": "0001018724", "NVDA": "0001045810", "META": "0001326801",
    "JPM": "0000019617", "GS": "0000886982", "BAC": "0000070858",
    "XOM": "0000034088", "CVX": "0000093410",
    "JNJ": "0000200406", "PFE": "0000078003", "UNH": "0000731766",
    "KO": "0000021344", "PG": "0000080424", "WMT": "0000104169",
    "COST": "0000909832", "TSLA": "0001318605", "BRK.B": "0001067983",
}

EDGAR_BASE = "https://www.sec.gov/cgi-bin/browse-edgar"
EDGAR_ARCHIVE = "https://www.sec.gov/Archives/edgar/data"
# A polite User-Agent is required by EDGAR. Use something identifiable.
USER_AGENT = "FinRAG Research finrag-research@example.com"


@dataclass
class Filing:
    """Metadata for one 10-K filing."""

    ticker: str
    cik: str
    filing_date: str       # YYYY-MM-DD
    fiscal_year: int
    accession_number: str  # e.g. 0000320193-23-000106
    form_type: str         # 10-K
    url: str               # direct link to the filing's primary document
    local_path: str        # path on disk after download

    def to_dict(self) -> dict:
        return asdict(self)


def _get_cik(ticker: str) -> str:
    """Resolve ticker to zero-padded CIK. Uses sec-edgar-api if available,
    falls back to the embedded table."""
    try:
        from sec_edgar_api import EdgarClient  # type: ignore

        client = EdgarClient(user_agent=USER_AGENT)
        # sec-edgar-api returns a 10-digit zero-padded CIK as a string
        cik = client.get_cik(ticker)
        if cik:
            return str(cik).zfill(10)
    except Exception as e:
        logger.debug(f"sec-edgar-api failed for {ticker}: {e}; using fallback")
    return FALLBACK_CIK.get(ticker.upper(), "")


def _fetch_filing_index(ticker: str, cik: str, form_type: str = "10-K") -> list[Filing]:
    """Fetch the list of 10-K filings for a CIK. Returns newest first.

    Uses the EDGAR JSON submissions API. Returns up to `limit` filings.
    """
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accs = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    report_dates = recent.get("reportDate", [])

    out: list[Filing] = []
    cik_num = str(int(cik))
    for i, form in enumerate(forms):
        if form != form_type:
            continue
        acc = accs[i].replace("-", "")
        acc_dashed = accs[i]
        primary = primary_docs[i]
        filing_url = f"{EDGAR_ARCHIVE}/{cik_num}/{acc}/{primary}"
        # reportDate is end of fiscal year (e.g. 2023-09-30 for Apple FY2023)
        fy = int(report_dates[i][:4]) if report_dates[i] else int(dates[i][:4])
        out.append(
            Filing(
                ticker=ticker,
                cik=cik,
                filing_date=dates[i],
                fiscal_year=fy,
                accession_number=acc_dashed,
                form_type=form,
                url=filing_url,
                local_path="",  # populated on download
            )
        )
    return out


def _download_filing(filing: Filing, raw_dir: Path) -> Filing:
    """Download the filing HTML to data/raw/{ticker}/{filing_date}/10k.html.

    Idempotent: skips download if the file already exists.
    """
    safe_date = filing.filing_date  # already YYYY-MM-DD
    target_dir = raw_dir / filing.ticker / safe_date
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "10k.html"
    if target.exists() and target.stat().st_size > 1024:
        logger.debug(f"Skip (exists): {target}")
        filing.local_path = str(target)
        return filing
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(filing.url, headers=headers, timeout=60)
    resp.raise_for_status()
    target.write_bytes(resp.content)
    logger.info(f"Downloaded {filing.ticker} {filing.filing_date} -> {target}")
    filing.local_path = str(target)
    return filing


def ingest(
    tickers: list[str] | None = None,
    raw_dir: Path = Path("./data/raw"),
    form_type: str = "10-K",
    years: int = 3,
    rate_limit_sec: float = 0.15,
) -> pd.DataFrame:
    """Ingest 10-K filings. Returns a DataFrame manifest.

    Args:
        tickers: list of tickers to pull. Defaults to DEFAULT_TICKERS.
        raw_dir: where to write raw HTML.
        form_type: '10-K' (annual) or '10-Q' (quarterly).
        years: how many years back to pull.
        rate_limit_sec: polite pause between EDGAR calls.

    Returns:
        DataFrame with columns matching `Filing.to_dict()`.
    """
    tickers = tickers or DEFAULT_TICKERS
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    all_filings: list[Filing] = []
    cutoff_year = datetime.now().year - years

    for t in tickers:
        cik = _get_cik(t)
        if not cik:
            logger.warning(f"Could not resolve CIK for {t}, skipping")
            continue
        try:
            filings = _fetch_filing_index(t, cik, form_type=form_type)
        except Exception as e:
            logger.warning(f"Failed to fetch index for {t}: {e}")
            continue
        # Filter to the last `years` years
        filings = [f for f in filings if f.fiscal_year >= cutoff_year]
        for f in filings:
            try:
                all_filings.append(_download_filing(f, raw_dir))
            except Exception as e:
                logger.warning(f"Failed to download {t} {f.filing_date}: {e}")
            time.sleep(rate_limit_sec)

    df = pd.DataFrame([f.to_dict() for f in all_filings])
    manifest_path = raw_dir / "filings.parquet"
    df.to_parquet(manifest_path, index=False)
    logger.info(f"Wrote manifest with {len(df)} filings to {manifest_path}")
    return df


def ingest_sample(raw_dir: Path = Path("./data/raw")) -> pd.DataFrame:
    """Ingest exactly one filing for the smoke test: Apple 10-K FY2023.

    Falls back to a tiny synthetic filing if EDGAR is unreachable so the
    pipeline can be exercised offline.
    """
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    target_dir = raw_dir / "AAPL" / "2023-11-03"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "10k.html"

    if not target.exists():
        try:
            cik = _get_cik("AAPL")
            filings = _fetch_filing_index("AAPL", cik, form_type="10-K")
            fy2023 = [f for f in filings if f.fiscal_year == 2023]
            if not fy2023:
                raise RuntimeError("No FY2023 10-K found in EDGAR index")
            _download_filing(fy2023[0], raw_dir)
        except Exception as e:
            logger.warning(
                f"Could not fetch AAPL FY2023 from EDGAR ({e}); "
                "writing a synthetic filing for the offline smoke test."
            )
            target.write_text(SYNTHETIC_AAPL_10K, encoding="utf-8")

    df = pd.DataFrame([
        {
            "ticker": "AAPL",
            "cik": "0000320193",
            "filing_date": "2023-11-03",
            "fiscal_year": 2023,
            "accession_number": "0000320193-23-000106",
            "form_type": "10-K",
            "url": "https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm",
            "local_path": str(target),
        }
    ])
    (raw_dir / "filings.parquet").write_text("")  # placeholder
    df.to_parquet(raw_dir / "filings.parquet", index=False)
    logger.info(f"Sample manifest written: {raw_dir / 'filings.parquet'}")
    return df


# A tiny synthetic 10-K used only for the offline smoke test when EDGAR
# is unreachable. Mirrors the structure of a real 10-K closely enough
# to exercise the section parser and chunker.
SYNTHETIC_AAPL_10K = """<!DOCTYPE html>
<html><head><title>Apple Inc. Form 10-K (Synthetic, for smoke test)</title></head>
<body>

<h1>UNITED STATES SECURITIES AND EXCHANGE COMMISSION</h1>
<p>Washington, D.C. 20549</p>
<h2>FORM 10-K</h2>

<p><b>ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934</b></p>
<p>For the fiscal year ended September 30, 2023.</p>
<p><b>Apple Inc.</b></p>

<h3>Item 1. Business</h3>
<p>Apple Inc. designs, manufactures and markets smartphones, personal computers,
tablets, wearables and accessories, and sells a variety of related services.
The Company's fiscal year is the 52- or 53-week period that ends on the last
Saturday of September. The Company is a California corporation established in
1977.</p>

<p>The Company sells its products and resells third-party products in most
of its primary markets directly to customers through its retail and online
stores and its direct sales force. The Company also employs a variety of
indirect distribution channels, such as third-party cellular network carriers,
wholesalers, retailers and resellers. During 2023, the Company's net sales
through its direct and indirect distribution channels were 38% and 62%,
respectively, of total net sales.</p>

<h3>Item 1A. Risk Factors</h3>
<p>Apple's business, reputation, results of operations, financial condition
and stock price can be affected by a number of factors, whether currently
known or unknown, including those described below. Any one or more of such
factors could directly or indirectly cause the Company's actual results of
operations and financial condition to vary materially from past, or from
anticipated future, results of operations and financial condition.</p>

<p><b>Macroeconomic and Industry Risks.</b> The Company's operations and
performance depend significantly on global and regional economic conditions
and adverse macroeconomic conditions can materially adversely affect the
Company's business, results of operations and financial condition.</p>

<p><b>Geopolitical Risk.</b> The Company has international operations with
sales in many countries. The Company is subject to risks related to
geopolitical events, trade disputes, foreign currency exchange rate
fluctuations and changes in tax laws, among other things.</p>

<p><b>Supply Chain Risk.</b> The Company depends on component supplies and
manufacturing services from a limited number of suppliers, including some
that are located in regions subject to geopolitical tensions.</p>

<h3>Item 7. Management's Discussion and Analysis of Financial Condition and Results of Operations</h3>
<p>The following discussion should be read in conjunction with the consolidated
financial statements and accompanying notes included in Part II, Item 8 of
this Form 10-K. This Item generally discusses 2023 and 2022 items and
year-to-year comparisons between 2023 and 2022. Discussions of 2021 items
and year-to-year comparisons between 2022 and 2021 that are not included
in this Form 10-K can be found in "Management's Discussion and Analysis
of Financial Condition and Results of Operations" in Part II, Item 7 of
the Company's Annual Report on Form 10-K for the fiscal year ended
September 30, 2022.</p>

<p><b>Net Sales.</b> Total net sales were $383.3 billion in 2023 compared to
$394.3 billion in 2022, a decrease of 3%.</p>

<p>Net sales by category for 2023 were as follows: iPhone $200.6 billion,
Mac $29.4 billion, iPad $28.3 billion, Wearables, Home and Accessories
$39.8 billion, and Services $85.2 billion.</p>

<p><b>Gross Margin.</b> Products and services gross margin was 37.6% in 2023
compared to 36.3% in 2022. The increase was primarily driven by cost savings
and a favorable shift in mix toward Services.</p>

<h3>Item 7A. Quantitative and Qualitative Disclosures About Market Risk</h3>
<p>The Company is exposed to financial market risks, including changes in
foreign currency exchange rates, interest rates and marketable equity security
prices. The Company uses derivative instruments to hedge certain exposures
and does not enter into derivative transactions for trading or speculative
purposes.</p>

<h3>Item 8. Financial Statements and Supplementary Data</h3>
<p>All financial statement schedules are omitted because they are not
applicable, the required information is shown in the consolidated financial
statements, or notes thereto, which are incorporated by reference herein.</p>

<p><b>Consolidated Statements of Operations.</b> Net sales: $383,285 (2023)
$394,328 (2022). Cost of sales: $214,137 (2023) $223,546 (2022). Gross
margin: $169,148 (2023) $170,782 (2022).</p>

</body></html>
"""
