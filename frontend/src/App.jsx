import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";

const STAGES = [
  { id: "news",    label: "Market Intelligence", icon: "◈", detail: "Scanning news & sentiment" },
  { id: "filing",  label: "SEC Filing Analysis",  icon: "◎", detail: "Parsing 10-K documents"    },
  { id: "finance", label: "Financial Modeling",   icon: "◆", detail: "Fetching live market data"  },
  { id: "risk",    label: "Risk Quantification",  icon: "◉", detail: "Stress-testing the model"  },
  { id: "memo",    label: "Memo Synthesis",       icon: "◇", detail: "Drafting investment thesis" },
];

const COMPANIES = [
  // ── Mega-cap Tech ──────────────────────────────────────────────────────────
  { ticker: "NVDA",  name: "NVIDIA Corporation",              sector: "Technology"   },
  { ticker: "AAPL",  name: "Apple Inc.",                      sector: "Technology"   },
  { ticker: "MSFT",  name: "Microsoft Corporation",           sector: "Technology"   },
  { ticker: "GOOGL", name: "Alphabet Inc. (Class A)",         sector: "Technology"   },
  { ticker: "META",  name: "Meta Platforms Inc.",             sector: "Technology"   },
  { ticker: "AVGO",  name: "Broadcom Inc.",                   sector: "Technology"   },
  { ticker: "ORCL",  name: "Oracle Corporation",              sector: "Technology"   },
  { ticker: "AMD",   name: "Advanced Micro Devices Inc.",     sector: "Technology"   },
  { ticker: "PLTR",  name: "Palantir Technologies Inc.",      sector: "Technology"   },
  { ticker: "CSCO",  name: "Cisco Systems Inc.",              sector: "Technology"   },
  { ticker: "IBM",   name: "IBM Corporation",                 sector: "Technology"   },
  { ticker: "INTC",  name: "Intel Corporation",               sector: "Technology"   },
  { ticker: "QCOM",  name: "Qualcomm Inc.",                   sector: "Technology"   },
  { ticker: "TXN",   name: "Texas Instruments Inc.",          sector: "Technology"   },
  { ticker: "AMAT",  name: "Applied Materials Inc.",          sector: "Technology"   },
  { ticker: "MU",    name: "Micron Technology Inc.",          sector: "Technology"   },
  { ticker: "LRCX",  name: "Lam Research Corporation",        sector: "Technology"   },
  { ticker: "KLAC",  name: "KLA Corporation",                 sector: "Technology"   },
  { ticker: "NOW",   name: "ServiceNow Inc.",                 sector: "Technology"   },
  { ticker: "ADBE",  name: "Adobe Inc.",                      sector: "Technology"   },
  { ticker: "CRM",   name: "Salesforce Inc.",                 sector: "Technology"   },
  { ticker: "NFLX",  name: "Netflix Inc.",                    sector: "Technology"   },
  { ticker: "PANW",  name: "Palo Alto Networks Inc.",         sector: "Technology"   },
  { ticker: "CRWD",  name: "CrowdStrike Holdings Inc.",       sector: "Technology"   },
  { ticker: "FTNT",  name: "Fortinet Inc.",                   sector: "Technology"   },
  { ticker: "SNDK",  name: "Sandisk Corporation",             sector: "Technology"   },
  { ticker: "WDC",   name: "Western Digital Corporation",     sector: "Technology"   },
  { ticker: "HPQ",   name: "HP Inc.",                         sector: "Technology"   },
  { ticker: "DELL",  name: "Dell Technologies Inc.",          sector: "Technology"   },
  { ticker: "ACN",   name: "Accenture plc",                   sector: "Technology"   },
  // ── Consumer / E-commerce ─────────────────────────────────────────────────
  { ticker: "AMZN",  name: "Amazon.com Inc.",                 sector: "Consumer"     },
  { ticker: "TSLA",  name: "Tesla Inc.",                      sector: "Consumer"     },
  { ticker: "WMT",   name: "Walmart Inc.",                    sector: "Consumer"     },
  { ticker: "COST",  name: "Costco Wholesale Corporation",    sector: "Consumer"     },
  { ticker: "HD",    name: "The Home Depot Inc.",             sector: "Consumer"     },
  { ticker: "MCD",   name: "McDonald's Corporation",          sector: "Consumer"     },
  { ticker: "PG",    name: "The Procter & Gamble Company",    sector: "Consumer"     },
  { ticker: "KO",    name: "The Coca-Cola Company",           sector: "Consumer"     },
  { ticker: "PEP",   name: "PepsiCo Inc.",                    sector: "Consumer"     },
  { ticker: "SBUX",  name: "Starbucks Corporation",           sector: "Consumer"     },
  { ticker: "NKE",   name: "Nike Inc.",                       sector: "Consumer"     },
  { ticker: "TGT",   name: "Target Corporation",              sector: "Consumer"     },
  { ticker: "LOW",   name: "Lowe's Companies Inc.",           sector: "Consumer"     },
  { ticker: "BKNG",  name: "Booking Holdings Inc.",           sector: "Consumer"     },
  { ticker: "ABNB",  name: "Airbnb Inc.",                     sector: "Consumer"     },
  { ticker: "GM",    name: "General Motors Company",          sector: "Consumer"     },
  { ticker: "F",     name: "Ford Motor Company",              sector: "Consumer"     },
  { ticker: "EBAY",  name: "eBay Inc.",                       sector: "Consumer"     },
  { ticker: "PM",    name: "Philip Morris International",     sector: "Consumer"     },
  { ticker: "RIVN",  name: "Rivian Automotive Inc.",          sector: "Consumer"     },
  // ── Financials ────────────────────────────────────────────────────────────
  { ticker: "BRK-B", name: "Berkshire Hathaway Inc. (B)",     sector: "Financials"   },
  { ticker: "JPM",   name: "JPMorgan Chase & Co.",            sector: "Financials"   },
  { ticker: "V",     name: "Visa Inc.",                       sector: "Financials"   },
  { ticker: "MA",    name: "Mastercard Incorporated",         sector: "Financials"   },
  { ticker: "GS",    name: "The Goldman Sachs Group Inc.",    sector: "Financials"   },
  { ticker: "BAC",   name: "Bank of America Corporation",     sector: "Financials"   },
  { ticker: "WFC",   name: "Wells Fargo & Company",           sector: "Financials"   },
  { ticker: "MS",    name: "Morgan Stanley",                  sector: "Financials"   },
  { ticker: "AXP",   name: "American Express Company",        sector: "Financials"   },
  { ticker: "C",     name: "Citigroup Inc.",                  sector: "Financials"   },
  { ticker: "BLK",   name: "BlackRock Inc.",                  sector: "Financials"   },
  { ticker: "SCHW",  name: "Charles Schwab Corporation",      sector: "Financials"   },
  { ticker: "PYPL",  name: "PayPal Holdings Inc.",            sector: "Financials"   },
  { ticker: "COF",   name: "Capital One Financial Corp.",     sector: "Financials"   },
  { ticker: "CB",    name: "Chubb Limited",                   sector: "Financials"   },
  { ticker: "ICE",   name: "Intercontinental Exchange Inc.",  sector: "Financials"   },
  { ticker: "CME",   name: "CME Group Inc.",                  sector: "Financials"   },
  { ticker: "COIN",  name: "Coinbase Global Inc.",            sector: "Financials"   },
  // ── Healthcare ────────────────────────────────────────────────────────────
  { ticker: "LLY",   name: "Eli Lilly and Company",           sector: "Healthcare"   },
  { ticker: "UNH",   name: "UnitedHealth Group Inc.",         sector: "Healthcare"   },
  { ticker: "JNJ",   name: "Johnson & Johnson",               sector: "Healthcare"   },
  { ticker: "ABBV",  name: "AbbVie Inc.",                     sector: "Healthcare"   },
  { ticker: "MRK",   name: "Merck & Co. Inc.",                sector: "Healthcare"   },
  { ticker: "ABT",   name: "Abbott Laboratories",             sector: "Healthcare"   },
  { ticker: "TMO",   name: "Thermo Fisher Scientific Inc.",   sector: "Healthcare"   },
  { ticker: "AMGN",  name: "Amgen Inc.",                      sector: "Healthcare"   },
  { ticker: "GILD",  name: "Gilead Sciences Inc.",            sector: "Healthcare"   },
  { ticker: "ISRG",  name: "Intuitive Surgical Inc.",         sector: "Healthcare"   },
  { ticker: "PFE",   name: "Pfizer Inc.",                     sector: "Healthcare"   },
  { ticker: "BMY",   name: "Bristol-Myers Squibb Company",    sector: "Healthcare"   },
  { ticker: "DHR",   name: "Danaher Corporation",             sector: "Healthcare"   },
  { ticker: "CVS",   name: "CVS Health Corporation",          sector: "Healthcare"   },
  { ticker: "CI",    name: "The Cigna Group",                 sector: "Healthcare"   },
  { ticker: "SYK",   name: "Stryker Corporation",             sector: "Healthcare"   },
  { ticker: "BSX",   name: "Boston Scientific Corporation",   sector: "Healthcare"   },
  { ticker: "REGN",  name: "Regeneron Pharmaceuticals Inc.",  sector: "Healthcare"   },
  { ticker: "VRTX",  name: "Vertex Pharmaceuticals Inc.",     sector: "Healthcare"   },
  // ── Energy ────────────────────────────────────────────────────────────────
  { ticker: "XOM",   name: "Exxon Mobil Corporation",         sector: "Energy"       },
  { ticker: "CVX",   name: "Chevron Corporation",             sector: "Energy"       },
  { ticker: "COP",   name: "ConocoPhillips",                  sector: "Energy"       },
  { ticker: "SLB",   name: "SLB (Schlumberger)",              sector: "Energy"       },
  { ticker: "EOG",   name: "EOG Resources Inc.",              sector: "Energy"       },
  { ticker: "PSX",   name: "Phillips 66",                     sector: "Energy"       },
  { ticker: "MPC",   name: "Marathon Petroleum Corporation",  sector: "Energy"       },
  { ticker: "OXY",   name: "Occidental Petroleum Corp.",      sector: "Energy"       },
  // ── Industrials ───────────────────────────────────────────────────────────
  { ticker: "GE",    name: "GE Aerospace",                    sector: "Industrials"  },
  { ticker: "GEV",   name: "GE Vernova Inc.",                 sector: "Industrials"  },
  { ticker: "CAT",   name: "Caterpillar Inc.",                sector: "Industrials"  },
  { ticker: "RTX",   name: "RTX Corporation",                 sector: "Industrials"  },
  { ticker: "LMT",   name: "Lockheed Martin Corporation",     sector: "Industrials"  },
  { ticker: "BA",    name: "The Boeing Company",              sector: "Industrials"  },
  { ticker: "HON",   name: "Honeywell International Inc.",    sector: "Industrials"  },
  { ticker: "NOC",   name: "Northrop Grumman Corporation",    sector: "Industrials"  },
  { ticker: "GD",    name: "General Dynamics Corporation",    sector: "Industrials"  },
  { ticker: "DE",    name: "Deere & Company",                 sector: "Industrials"  },
  { ticker: "UPS",   name: "United Parcel Service Inc.",      sector: "Industrials"  },
  { ticker: "FDX",   name: "FedEx Corporation",               sector: "Industrials"  },
  { ticker: "MMM",   name: "3M Company",                      sector: "Industrials"  },
  { ticker: "LIN",   name: "Linde plc",                       sector: "Industrials"  },
  // ── Telecom & Media ───────────────────────────────────────────────────────
  { ticker: "TMUS",  name: "T-Mobile US Inc.",                sector: "Telecom"      },
  { ticker: "VZ",    name: "Verizon Communications Inc.",     sector: "Telecom"      },
  { ticker: "T",     name: "AT&T Inc.",                       sector: "Telecom"      },
  { ticker: "DIS",   name: "The Walt Disney Company",         sector: "Media"        },
  { ticker: "CMCSA", name: "Comcast Corporation",             sector: "Media"        },
  { ticker: "SPOT",  name: "Spotify Technology S.A.",         sector: "Media"        },
  // ── Utilities ─────────────────────────────────────────────────────────────
  { ticker: "NEE",   name: "NextEra Energy Inc.",             sector: "Utilities"    },
  { ticker: "DUK",   name: "Duke Energy Corporation",         sector: "Utilities"    },
  { ticker: "SO",    name: "The Southern Company",            sector: "Utilities"    },
  { ticker: "D",     name: "Dominion Energy Inc.",            sector: "Utilities"    },
  // ── Fintech ───────────────────────────────────────────────────────────────
  { ticker: "SQ",    name: "Block Inc.",                      sector: "Fintech"      },
  { ticker: "AFRM",  name: "Affirm Holdings Inc.",            sector: "Fintech"      },
  { ticker: "SOFI",  name: "SoFi Technologies Inc.",          sector: "Fintech"      },
  { ticker: "HOOD",  name: "Robinhood Markets Inc.",          sector: "Fintech"      },
  // ── AI / Cloud / Cybersecurity ────────────────────────────────────────────
  { ticker: "ARM",   name: "Arm Holdings plc",                sector: "Technology"   },
  { ticker: "SNOW",  name: "Snowflake Inc.",                  sector: "Technology"   },
  { ticker: "DDOG",  name: "Datadog Inc.",                    sector: "Technology"   },
  { ticker: "NET",   name: "Cloudflare Inc.",                 sector: "Technology"   },
  { ticker: "ZS",    name: "Zscaler Inc.",                    sector: "Technology"   },
  { ticker: "UBER",  name: "Uber Technologies Inc.",          sector: "Technology"   },
];

// Deduplicate by ticker
const seen = new Set();
const UNIQUE_COMPANIES = COMPANIES.filter(c => {
  if (seen.has(c.ticker)) return false;
  seen.add(c.ticker);
  return true;
});

const SECTOR_COLORS = {
  Technology:  "#3b82f6",
  Financials:  "#22c55e",
  Healthcare:  "#a78bfa",
  Consumer:    "#f59e0b",
  Energy:      "#fb923c",
  Industrials: "#94a3b8",
  Utilities:   "#06b6d4",
  Media:       "#ec4899",
  Telecom:     "#14b8a6",
  Fintech:     "#34d399",
};

function TickerInput({ onSubmit, loading }) {
  const [value,        setValue]        = useState("");
  const [focused,      setFocused]      = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [highlighted,  setHighlighted]  = useState(0);
  const [dropdownPos,  setDropdownPos]  = useState(null);
  const inputRef = useRef(null);
  const wrapRef  = useRef(null);

  // ── THE FIX: no slice when empty — show ALL companies ────────────────────
  const filtered = value.length === 0
    ? UNIQUE_COMPANIES
    : UNIQUE_COMPANIES.filter(c =>
        c.ticker.startsWith(value) ||
        c.name.toLowerCase().includes(value.toLowerCase())
      ).slice(0, 15);

  useEffect(() => {
    if (showDropdown && wrapRef.current) {
      const rect = wrapRef.current.getBoundingClientRect();
      setDropdownPos({
        top:   rect.bottom + 2,
        left:  rect.left,
        width: rect.width,
      });
    }
  }, [showDropdown, value]);

  const handle = (e) => {
    e.preventDefault();
    if (value.trim()) { onSubmit(value.trim().toUpperCase()); setShowDropdown(false); }
  };

  const pick = (ticker) => {
    setValue(ticker);
    setShowDropdown(false);
    onSubmit(ticker);
  };

  const onKeyDown = (e) => {
    if (!showDropdown) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setHighlighted(h => Math.min(h + 1, filtered.length - 1)); }
    if (e.key === "ArrowUp")   { e.preventDefault(); setHighlighted(h => Math.max(h - 1, 0)); }
    if (e.key === "Enter" && filtered[highlighted]) { e.preventDefault(); pick(filtered[highlighted].ticker); }
    if (e.key === "Escape") setShowDropdown(false);
  };

  const dropdownPortal = showDropdown && filtered.length > 0 && dropdownPos
    ? createPortal(
        <div style={{
          position:   "fixed",
          top:        dropdownPos.top,
          left:       dropdownPos.left,
          width:      dropdownPos.width,
          zIndex:     99999,
          background: "#0d1626",
          border:     "1px solid #3b82f6",
          borderRadius: "0 0 8px 8px",
          overflowX:  "hidden",
          overflowY:  "scroll",
          WebkitOverflowScrolling: "touch",
          maxHeight:  `${Math.min(400, window.innerHeight - dropdownPos.top - 16)}px`,
          boxShadow:  "0 24px 64px rgba(0,0,0,0.85)",
          fontFamily: "'JetBrains Mono', monospace",
        }}>
          {/* Sticky header */}
          <div style={{
            position: "sticky", top: 0,
            padding: "6px 14px",
            fontSize: "8px", letterSpacing: "0.28em", color: "#4d6b8a",
            background: "#080f1c",
            borderBottom: "1px solid #1a2d4a",
          }}>
            {value.length === 0
              ? `ALL STOCKS — ${UNIQUE_COMPANIES.length} COMPANIES`
              : `${filtered.length} RESULT${filtered.length !== 1 ? "S" : ""}`}
          </div>

          {/* Company rows */}
          {filtered.map((c, i) => (
            <div
              key={c.ticker}
              onMouseDown={() => pick(c.ticker)}
              onMouseEnter={() => setHighlighted(i)}
              style={{
                display: "flex", alignItems: "center", gap: "12px",
                padding: "10px 14px", cursor: "pointer",
                borderBottom: "1px solid rgba(26,45,74,0.4)",
                background: i === highlighted ? "#111e35" : "transparent",
                transition: "background 0.1s",
              }}
            >
              <span style={{
                minWidth: "60px", fontSize: "12px", fontWeight: "700",
                letterSpacing: "0.05em",
                color: SECTOR_COLORS[c.sector] || "#3b82f6",
              }}>
                {c.ticker}
              </span>
              <span style={{
                flex: 1, fontSize: "11px", color: "#7a99bb",
                whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
              }}>
                {c.name}
              </span>
              <span style={{
                fontSize: "8px", letterSpacing: "0.1em",
                color: SECTOR_COLORS[c.sector] || "#4d6b8a",
                opacity: 0.7, whiteSpace: "nowrap",
              }}>
                {c.sector}
              </span>
            </div>
          ))}

          {/* Sticky footer */}
          <div style={{
            position: "sticky", bottom: 0,
            padding: "6px 14px",
            fontSize: "9px", fontStyle: "italic", letterSpacing: "0.06em",
            color: "#4d6b8a", background: "#080f1c",
            borderTop: "1px solid #1a2d4a",
          }}>
            Type any ticker not listed — we'll analyze it
          </div>
        </div>,
        document.body
      )
    : null;

  return (
    <div className="input-section">
      <div className="input-label">SEARCH COMPANY OR TICKER</div>
      <form onSubmit={handle} className="input-row">
        <div className={`input-wrap ${focused ? "focused" : ""}`} ref={wrapRef}>
          <span className="input-prefix">$</span>
          <input
            ref={inputRef}
            value={value}
            onChange={e => { setValue(e.target.value.toUpperCase()); setShowDropdown(true); setHighlighted(0); }}
            onFocus={() => { setFocused(true); setShowDropdown(true); }}
            onBlur={() => { setFocused(false); setTimeout(() => setShowDropdown(false), 200); }}
            onKeyDown={onKeyDown}
            placeholder="e.g. AAPL or Apple"
            maxLength={10}
            disabled={loading}
            autoComplete="off"
            spellCheck="false"
          />
        </div>
        <button type="submit" disabled={loading || !value.trim()} className="run-btn">
          {loading ? <span className="btn-spinner" /> : <>ANALYZE <span className="btn-arrow">→</span></>}
        </button>
      </form>
      {dropdownPortal}
    </div>
  );
}

function ProgressPanel({ stage, stages, elapsed }) {
  const current = stages.findIndex(s => s.id === stage);
  return (
    <div className="progress-panel">
      <div className="progress-header">
        <span className="progress-title">PIPELINE RUNNING</span>
        <span className="elapsed">{elapsed}s</span>
      </div>
      <div className="stages">
        {stages.map((s, i) => {
          const done   = i < current;
          const active = i === current;
          return (
            <div key={s.id} className={`stage ${done ? "done" : active ? "active" : "pending"}`}>
              <div className="stage-track">
                <div className={`stage-dot ${done ? "done" : active ? "active pulse" : ""}`}>
                  {done ? "✓" : s.icon}
                </div>
                {i < stages.length - 1 && <div className={`stage-line ${done ? "done" : ""}`} />}
              </div>
              <div className="stage-info">
                <div className="stage-label">{s.label}</div>
                {active && <div className="stage-detail">{s.detail}</div>}
              </div>
            </div>
          );
        })}
      </div>
      <div className="progress-bar-wrap">
        <div className="progress-bar" style={{ width: `${Math.max(5, (current / stages.length) * 100)}%` }} />
      </div>
    </div>
  );
}

function RiskGauge({ score }) {
  const level = score <= 3 ? "LOW" : score <= 6 ? "MEDIUM" : score <= 8 ? "HIGH" : "VERY HIGH";
  const color = score <= 3 ? "#22c55e" : score <= 6 ? "#f59e0b" : score <= 8 ? "#ef4444" : "#9333ea";
  const angle = -135 + (score / 10) * 270;
  const r = 54; const cx = 70; const cy = 72;
  const toRad = d => (d * Math.PI) / 180;
  const arcX  = cx + r * Math.cos(toRad(angle));
  const arcY  = cy + r * Math.sin(toRad(angle));
  return (
    <div className="gauge-wrap">
      <svg width="140" height="110" viewBox="0 0 140 110">
        <defs>
          <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%"   stopColor="#22c55e" />
            <stop offset="40%"  stopColor="#f59e0b" />
            <stop offset="70%"  stopColor="#ef4444" />
            <stop offset="100%" stopColor="#9333ea" />
          </linearGradient>
        </defs>
        <path d="M 16,72 A 54,54 0 1 1 124,72" fill="none" stroke="#1e293b"         strokeWidth="10" strokeLinecap="round" />
        <path d="M 16,72 A 54,54 0 1 1 124,72" fill="none" stroke="url(#gaugeGrad)" strokeWidth="10" strokeLinecap="round" strokeOpacity="0.3" />
        <line x1={cx} y1={cy} x2={arcX} y2={arcY} stroke={color} strokeWidth="3" strokeLinecap="round" />
        <circle cx={cx} cy={cy} r="5" fill={color} />
        <text x={cx} y={cy + 20} textAnchor="middle" fill="white" fontSize="18" fontWeight="700" fontFamily="monospace">{score}/10</text>
        <text x={cx} y={cy + 33} textAnchor="middle" fill={color} fontSize="7"  fontWeight="600" letterSpacing="2" fontFamily="monospace">{level}</text>
      </svg>
    </div>
  );
}

function MetricCard({ label, value }) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value ?? "—"}</div>
    </div>
  );
}

function ResultPanel({ data, ticker, onReset, onDownload, downloading }) {
  const fin             = data.financial_data   || {};
  const risk_assessment = data.risk_assessment  || "";
  const investment_memo = data.investment_memo  || "";
  const recommendation  = data.recommendation   || fin.analyst_recommendation || "N/A";

  const riskScore = (() => {
    const m = risk_assessment.match(/RISK SCORE:\s*(\d+)/i);
    return m ? parseInt(m[1]) : null;
  })();

  const riskLevel = (() => {
    const m = risk_assessment.match(/OVERALL RISK LEVEL:\s*(\w+)/i);
    return m ? m[1].trim() : null;
  })();

  const sections = investment_memo
    .split(/\n## /)
    .map((s, i) => {
      if (i === 0) return null;
      const lines = s.split("\n");
      return { title: lines[0].replace(/^#+\s*/, ""), body: lines.slice(1).join("\n").trim() };
    })
    .filter(Boolean);

  const riskColor = !riskScore ? "#94a3b8"
    : riskScore <= 3 ? "#22c55e"
    : riskScore <= 6 ? "#f59e0b"
    : riskScore <= 8 ? "#ef4444" : "#9333ea";

  const recUpper = String(recommendation).toUpperCase();
  const recColor = recUpper.includes("BUY") ? "#22c55e"
    : recUpper === "HOLD" ? "#f59e0b" : "#ef4444";

  const fmtPrice = (v) => {
    if (!v || v === "N/A") return "—";
    const n = parseFloat(String(v).replace(/[^0-9.]/g, ""));
    return isNaN(n) ? String(v) : `$${n.toFixed(2)}`;
  };

  return (
    <div className="result-panel">
      <div className="result-header">
        <div className="result-ticker-block">
          <span className="result-ticker">{ticker}</span>
          <span className="result-company">{data.company_name}</span>
          <span className="result-date">
            {new Date().toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })}
          </span>
        </div>
        <div className="result-actions">
          <button className="action-btn secondary" onClick={onReset}>← NEW ANALYSIS</button>
          <button className="action-btn primary" onClick={onDownload} disabled={downloading}>
            {downloading ? <><span className="btn-spinner sm" /> GENERATING…</> : <>↓ DOWNLOAD PDF</>}
          </button>
        </div>
      </div>

      <div className="hero-metrics">
        <div className="hero-rec" style={{ borderColor: recColor, color: recColor }}>
          <div className="hero-rec-label">RECOMMENDATION</div>
          <div className="hero-rec-value">{recUpper}</div>
        </div>
        <div className="hero-price">
          <MetricCard label="CURRENT PRICE"    value={fmtPrice(fin.current_price)} />
          <MetricCard label="PRICE TARGET"     value={fmtPrice(fin.target_price)} />
          <MetricCard label="ANALYST COVERAGE" value={fin.number_of_analysts ? `${fin.number_of_analysts} analysts` : "—"} />
          <MetricCard label="MARKET CAP"       value={fin.market_cap ?? "—"} />
        </div>
      </div>

      <div className="result-grid">
        <div className="financials-col">
          <div className="section-head">FINANCIAL SNAPSHOT</div>
          <div className="fin-table">
            {[
              ["Revenue (TTM)",    fin.revenue_ttm],
              ["Net Income",       fin.net_income],
              ["Gross Profit",     fin.gross_profit],
              ["EBITDA",           fin.ebitda],
              ["Gross Margin",     fin.gross_margin],
              ["Operating Margin", fin.operating_margin],
              ["Net Margin",       fin.net_margin],
              ["P/E Ratio",        fin.pe_ratio],
              ["Forward P/E",      fin.forward_pe],
              ["EV/EBITDA",        fin.ev_ebitda],
              ["Revenue Growth",   fin.revenue_growth],
              ["Earnings Growth",  fin.earnings_growth],
              ["Total Debt",       fin.total_debt],
              ["Cash",             fin.cash],
              ["Current Ratio",    fin.current_ratio],
              ["Debt/Equity",      fin.debt_to_equity],
              ["Return on Equity", fin.roe],
            ].map(([label, val]) => (
              <div key={label} className="fin-row">
                <span className="fin-label">{label}</span>
                <span className={`fin-val ${!val || val === "N/A" ? "na" : ""}`}>
                  {val && val !== "N/A" ? val : "—"}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="analysis-col">
          <div className="risk-block">
            <div className="section-head">RISK ASSESSMENT</div>
            <div className="risk-inner">
              {riskScore && <RiskGauge score={riskScore} />}
              <div className="risk-text">
                <div className="risk-level" style={{ color: riskColor }}>{riskLevel || "—"}</div>
                <div className="risk-factors">
                  {risk_assessment.split("\n")
                    .filter(l => /^\d+\./.test(l.trim()))
                    .map((l, i) => (
                      <div key={i} className="risk-factor-line">
                        <span className="risk-dot" style={{ background: riskColor }} />
                        <span>{l.replace(/^\d+\.\s*\*{0,2}/, "").replace(/\*{0,2}$/, "")}</span>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          </div>

          <div className="memo-sections">
            <div className="section-head">INVESTMENT MEMO</div>
            {sections.length > 0 ? sections.map((sec, i) => (
              <div key={i} className="memo-section">
                <div className="memo-section-title">{sec.title}</div>
                <div className="memo-section-body">
                  {sec.body.split("\n").map((line, j) => {
                    const clean = line.replace(/^\*+\s*/, "").replace(/\*\*(.*?)\*\*/g, "$1").trim();
                    if (!clean) return null;
                    const isBullet = /^[-•*]/.test(line.trim()) || /^\d+\./.test(line.trim());
                    return isBullet
                      ? <div key={j} className="memo-bullet"><span className="memo-bullet-dot">›</span>{clean}</div>
                      : <p key={j} className="memo-para">{clean}</p>;
                  })}
                </div>
              </div>
            )) : (
              <div className="memo-para" style={{ color: "var(--text-dim)" }}>
                {investment_memo || "No memo available."}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [mode,        setMode]        = useState("idle");
  const [ticker,      setTicker]      = useState("");
  const [stage,       setStage]       = useState(null);
  const [result,      setResult]      = useState(null);
  const [error,       setError]       = useState(null);
  const [elapsed,     setElapsed]     = useState(0);
  const [downloading, setDownloading] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => {
    if (mode === "loading") {
      timerRef.current = setInterval(() => setElapsed(e => e + 1), 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [mode]);

  const simulate = (stages, idx, resolve) => {
    if (idx >= stages.length) return resolve();
    setStage(stages[idx].id);
    setTimeout(() => simulate(stages, idx + 1, resolve), 2200 + Math.random() * 2800);
  };

  const handleSubmit = async (t) => {
    setTicker(t);
    setMode("loading");
    setElapsed(0);
    setError(null);
    setResult(null);
    setStage(STAGES[0].id);
    const stagePromise = new Promise(r => simulate(STAGES, 0, r));
    try {
      const res = await fetch("/research", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ ticker: t }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Server error ${res.status}`);
      }
      const data = await res.json();
      await stagePromise;
      setResult(data);
      setMode("done");
    } catch (e) {
      await stagePromise;
      setError(e.message);
      setMode("error");
    }
  };

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const res = await fetch(`/pdf/${ticker}`);
      if (!res.ok) throw new Error("PDF not ready — run analysis first");
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href = url;
      a.download = `${ticker}_memo_${new Date().toISOString().slice(0, 10)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("PDF download failed: " + e.message);
    } finally {
      setDownloading(false);
    }
  };

  const handleReset = () => {
    setMode("idle"); setTicker(""); setResult(null); setError(null); setStage(null);
  };

  return (
    <div className="app">
      <div className="bg-grid" />
      <div className="bg-glow" />

      <header className="topbar">
        <div className="logo">
          <span className="logo-mark">▲</span>
          <span className="logo-text">ALPHA<span className="logo-accent">DESK</span></span>
        </div>
        <div className="topbar-right">
          <span className="topbar-tag">AI EQUITY RESEARCH</span>
          <div className="live-dot" />
          <span className="live-label">LIVE</span>
        </div>
      </header>

      <main className="main">
        {mode === "idle" && (
          <div className="hero">
            <div className="hero-eyebrow">INSTITUTIONAL-GRADE ANALYSIS</div>
            <h1 className="hero-title">
              AI-Powered<br />
              <span className="hero-accent">Equity Research</span>
            </h1>
            <p className="hero-sub">
              Multi-agent pipeline combining SEC filings, live market data,<br />
              and LLM synthesis to generate professional investment memos.
            </p>
            <TickerInput onSubmit={handleSubmit} loading={false} />
            <div className="hero-features" style={{ position: "relative", zIndex: 0 }}>
              {["SEC 10-K Analysis", "Yahoo Finance Data", "Risk Quantification", "PDF Export"].map(f => (
                <div key={f} className="feature-pill">
                  <span className="feature-check">✓</span> {f}
                </div>
              ))}
            </div>
          </div>
        )}

        {mode === "loading" && (
          <div className="loading-view">
            <div className="loading-ticker">{ticker}</div>
            <div className="loading-sub">Running multi-agent analysis pipeline</div>
            <ProgressPanel stage={stage} stages={STAGES} elapsed={elapsed} />
          </div>
        )}

        {mode === "done" && result && (
          <ResultPanel
            data={result}
            ticker={ticker}
            onReset={handleReset}
            onDownload={handleDownload}
            downloading={downloading}
          />
        )}

        {mode === "error" && (
          <div className="error-view">
            <div className="error-icon">⚠</div>
            <div className="error-title">Analysis Failed</div>
            <div className="error-msg">{error}</div>
            <div className="error-hint">
              Make sure FastAPI is running: <code>uvicorn api.main:app --reload --port 8000</code>
            </div>
            <button className="action-btn secondary" onClick={handleReset}>← TRY AGAIN</button>
          </div>
        )}
      </main>
    </div>
  );
}