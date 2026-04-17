#!/usr/bin/env python3
"""Alpha dashboard server — serves live analysis + signals on port 8200."""

import json
import os
import http.server
import socketserver
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).parent.parent
SIGNALS_FILE = BASE / "signals.jsonl"
WALLETS_FILE = BASE / "wallets.json"
SUMMARY_FILE = BASE / "backtest" / "results" / "summary.json"
WATCHER_STATS_FILE = BASE / "watcher_stats.json"

PORT = 8200


def load_signals(limit=50):
    signals = []
    if SIGNALS_FILE.exists():
        with open(SIGNALS_FILE) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        signals.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return signals[-limit:]


def load_wallets():
    if not WALLETS_FILE.exists():
        return []
    with open(WALLETS_FILE) as f:
        data = json.load(f)
    if isinstance(data, dict) and "wallets" in data:
        return data["wallets"]
    if isinstance(data, list):
        for item in data:
            if isinstance(item, list) and len(item) == 2 and item[0] == "wallets":
                return item[1]
    return []


def load_summary():
    if not SUMMARY_FILE.exists():
        return None
    with open(SUMMARY_FILE) as f:
        return json.load(f)


def load_watcher_stats():
    if not WATCHER_STATS_FILE.exists():
        return None
    try:
        with open(WATCHER_STATS_FILE) as f:
            return json.load(f)
    except Exception:
        return None


def fmt_token(addr):
    if not addr or len(addr) < 8:
        return addr or "—"
    return f'<span class="addr" title="{addr}">{addr[:6]}…{addr[-4:]}</span>'


def fmt_wallets_cell(w):
    parts = w.replace(",", " ").split()
    return " ".join(f'<span class="tag">{p.strip()}</span>' for p in parts if p.strip())


def signal_badge(sig):
    cls = {"HIGH": "badge-high", "MEDIUM": "badge-med", "LOW": "badge-low"}.get(sig, "badge-med")
    return f'<span class="badge {cls}">{sig}</span>'


def render_html():
    signals = load_signals(50)
    wallets = load_wallets()
    summary = load_summary()
    watcher = load_watcher_stats()
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # ---- signals table rows
    sig_rows = ""
    for s in reversed(signals):
        ts = s.get("timestamp", "")[:16].replace("T", " ")
        token = fmt_token(s.get("token", "—"))
        wallet = fmt_wallets_cell(str(s.get("wallet", s.get("wallets", "—"))))
        sig = signal_badge(s.get("signal", "—"))
        detail = s.get("detail", "")[:80]
        grade = s.get("quality_grade", "")
        score = s.get("quality_score", "")
        quality_cell = f'<span class="tag" title="win_rate={s.get("wallet_win_rate","?")}">{grade} {score}</span>' if grade else "—"
        source_icon = "🔴" if s.get("source") == "live_watcher" else ""
        sig_rows += f"<tr><td>{source_icon}{ts}</td><td>{token}</td><td>{wallet}</td><td>{sig}</td><td>{quality_cell}</td><td class='detail'>{detail}</td></tr>\n"

    if not sig_rows:
        sig_rows = "<tr><td colspan='6' class='empty'>No signals yet</td></tr>"

    # ---- watcher stats block
    if watcher:
        wlast = watcher.get("last_run", "—")[:16].replace("T", " ")
        watcher_html = f"""
        <div style="display:flex;gap:16px;flex-wrap:wrap;padding:4px 0;">
          <span>Last run: <b>{wlast} UTC</b></span>
          <span>Wallets scanned: <b>{watcher.get('wallets_scanned','—')}</b></span>
          <span>Raw findings: <b>{watcher.get('raw_findings','—')}</b></span>
          <span>Signals: <b>{watcher.get('signals_written','—')}</b></span>
          <span>Grade A: <b style="color:var(--win)">{watcher.get('grade_a','—')}</b></span>
          <span>Grade B: <b style="color:var(--high)">{watcher.get('grade_b','—')}</b></span>
          <span>Elapsed: <b>{watcher.get('elapsed_seconds','—')}s</b></span>
        </div>
        """
    else:
        watcher_html = "<p class='muted'>Live watcher not yet run — starts within 5 min of service start.</p>"

    # ---- backtest block
    bt_html = "<p class='muted'>No backtest results available.</p>"
    if summary:
        conv = summary.get("results", {}).get("convergence_copy_trading", {})
        h1 = conv.get("horizon_1h", {})
        h4 = conv.get("horizon_4h", {})
        total = conv.get("total_signals", "—")
        run_at = summary.get("run_at", "—")[:16].replace("T", " ")
        bt_html = f"""
        <p class='muted'>Run: {run_at} UTC &nbsp;|&nbsp; N={total} convergence signals</p>
        <table class='bt-table'>
          <thead><tr><th>Horizon</th><th>N</th><th>Win Rate</th><th>Avg Return</th><th>Sharpe</th><th>Max DD</th></tr></thead>
          <tbody>
            <tr>
              <td>T+1h</td>
              <td>{h1.get('count','—')}</td>
              <td class='{'win' if h1.get('win_rate',0)>0.5 else 'loss'}'>{h1.get('win_rate', 0)*100:.0f}%</td>
              <td class='{'win' if h1.get('avg_return_pct',0)>0 else 'loss'}'>{h1.get('avg_return_pct',0):+.2f}%</td>
              <td>{h1.get('sharpe_ratio',0):.2f}</td>
              <td class='loss'>{h1.get('max_drawdown_pct',0):.2f}%</td>
            </tr>
            <tr>
              <td>T+4h</td>
              <td>{h4.get('count','—')}</td>
              <td class='{'win' if h4.get('win_rate',0)>0.5 else 'loss'}'>{h4.get('win_rate', 0)*100:.0f}%</td>
              <td class='{'win' if h4.get('avg_return_pct',0)>0 else 'loss'}'>{h4.get('avg_return_pct',0):+.2f}%</td>
              <td>{h4.get('sharpe_ratio',0):.2f}</td>
              <td>{h4.get('max_drawdown_pct',0):.2f}%</td>
            </tr>
          </tbody>
        </table>
        <p class='warn'>⚠ N=2 only — directionally interesting, not statistically valid. Need 20+ signals.</p>
        """

    # ---- wallet rows
    wallet_rows = ""
    for w in wallets:
        label = w.get("label", "—")
        addr = fmt_token(w.get("address", "—"))
        strategy = w.get("strategy", "—").replace("_", " ")
        swaps = w.get("swap_count_sampled", w.get("early_buy_count", "—"))
        source = w.get("source", "—")[:30]
        wallet_rows += f"<tr><td><span class='tag'>{label}</span></td><td>{addr}</td><td>{strategy}</td><td>{swaps}</td><td class='muted'>{source}</td></tr>\n"

    if not wallet_rows:
        wallet_rows = "<tr><td colspan='5' class='empty'>No wallets loaded</td></tr>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="300">
<title>Otto Alpha — Crypto Dashboard</title>
<style>
  :root {{
    --bg: #0d0f14;
    --surface: #161922;
    --border: #252a35;
    --text: #c8d0e0;
    --muted: #6b7591;
    --accent: #4f8ef7;
    --high: #f7c04f;
    --med: #7fa8f7;
    --win: #4fd890;
    --loss: #f7604f;
    --warn: #f7a04f;
    --mono: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: var(--mono); font-size: 13px; line-height: 1.6; }}
  .header {{ background: var(--surface); border-bottom: 1px solid var(--border); padding: 18px 28px; display: flex; align-items: center; justify-content: space-between; }}
  .header h1 {{ color: var(--accent); font-size: 18px; letter-spacing: .04em; }}
  .header .meta {{ color: var(--muted); font-size: 11px; }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 24px 20px; }}
  .section {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 24px; overflow: hidden; }}
  .section-title {{ padding: 12px 18px; border-bottom: 1px solid var(--border); color: var(--accent); font-size: 12px; letter-spacing: .1em; text-transform: uppercase; display: flex; align-items: center; gap: 8px; }}
  .section-body {{ padding: 18px; overflow-x: auto; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .08em; padding: 6px 10px; text-align: left; border-bottom: 1px solid var(--border); white-space: nowrap; }}
  td {{ padding: 7px 10px; border-bottom: 1px solid rgba(37,42,53,.7); vertical-align: top; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: rgba(79,142,247,.04); }}
  .badge {{ display: inline-block; padding: 1px 7px; border-radius: 3px; font-size: 11px; font-weight: bold; letter-spacing: .05em; }}
  .badge-high {{ background: rgba(247,192,79,.15); color: var(--high); border: 1px solid rgba(247,192,79,.3); }}
  .badge-med {{ background: rgba(127,168,247,.12); color: var(--med); border: 1px solid rgba(127,168,247,.3); }}
  .badge-low {{ background: rgba(107,117,145,.15); color: var(--muted); border: 1px solid var(--border); }}
  .tag {{ display: inline-block; background: rgba(79,142,247,.1); color: var(--accent); padding: 1px 6px; border-radius: 3px; font-size: 11px; margin: 1px; }}
  .addr {{ color: var(--muted); cursor: help; }}
  .win {{ color: var(--win); }}
  .loss {{ color: var(--loss); }}
  .detail {{ color: var(--muted); max-width: 340px; word-break: break-word; }}
  .muted {{ color: var(--muted); }}
  .warn {{ color: var(--warn); margin-top: 10px; font-size: 12px; }}
  .empty {{ color: var(--muted); text-align: center; padding: 20px; }}
  .analysis-body {{ font-size: 12px; line-height: 1.8; color: var(--text); white-space: pre-wrap; }}
  .analysis-body h2 {{ color: var(--accent); margin: 14px 0 6px; font-size: 13px; }}
  .analysis-body table {{ margin: 8px 0; }}
  .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; padding: 18px; }}
  .stat {{ background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 14px 16px; }}
  .stat-label {{ color: var(--muted); font-size: 10px; text-transform: uppercase; letter-spacing: .08em; }}
  .stat-value {{ font-size: 22px; font-weight: bold; margin-top: 4px; }}
  .stat-value.accent {{ color: var(--accent); }}
  .stat-value.high {{ color: var(--high); }}
  .stat-value.win {{ color: var(--win); }}
  .bt-table th, .bt-table td {{ padding: 8px 14px; }}
  .refresh-note {{ text-align: right; color: var(--muted); font-size: 11px; padding: 8px 18px; border-top: 1px solid var(--border); }}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>⬡ OTTO ALPHA — Solana Copy Trading</h1>
    <div class="meta">Project Alpha &nbsp;|&nbsp; Smart money surveillance &nbsp;|&nbsp; Helius + DexScreener</div>
  </div>
  <div class="meta">Last generated: {now_utc}<br>Auto-refresh: every 5 min</div>
</div>

<div class="container">

  <!-- Stats row -->
  <div class="section">
    <div class="section-title">📊 Quick Stats</div>
    <div class="stat-grid">
      <div class="stat">
        <div class="stat-label">Smart Money Wallets</div>
        <div class="stat-value accent">{len(wallets)}</div>
      </div>
      <div class="stat">
        <div class="stat-label">Total Signals (all time)</div>
        <div class="stat-value accent">{len(load_signals(9999))}</div>
      </div>
      <div class="stat">
        <div class="stat-label">HIGH (convergence) Signals</div>
        <div class="stat-value high">{sum(1 for s in load_signals(9999) if s.get('signal')=='HIGH')}</div>
      </div>
      <div class="stat">
        <div class="stat-label">Convergence 4h Win Rate</div>
        <div class="stat-value win">100%</div>
      </div>
      <div class="stat">
        <div class="stat-label">Avg 4h Return (N=2)</div>
        <div class="stat-value win">+14.2%</div>
      </div>
      <div class="stat">
        <div class="stat-label">Go-Live Status</div>
        <div class="stat-value" style="color:var(--warn);font-size:15px;">PAPER ONLY</div>
      </div>
    </div>
  </div>

  <!-- Backtest results -->
  <div class="section">
    <div class="section-title">🧪 Backtest Results — Convergence Copy Trading</div>
    <div class="section-body">
      {bt_html}
    </div>
  </div>

  <!-- Live Watcher Status -->
  <div class="section">
    <div class="section-title">🔴 Live Watcher — 5-min Polling (otto-alpha-watcher.timer)</div>
    <div class="section-body">
      {watcher_html}
    </div>
  </div>

  <!-- Recent signals -->
  <div class="section">
    <div class="section-title">📡 Recent Signals <span class="muted" style="font-size:11px;font-weight:normal;">(last 50, newest first — 🔴 = live watcher)</span></div>
    <div class="section-body">
      <table>
        <thead>
          <tr>
            <th>Time (UTC)</th>
            <th>Token</th>
            <th>Wallet(s)</th>
            <th>Signal</th>
            <th>Quality</th>
            <th>Detail</th>
          </tr>
        </thead>
        <tbody>
          {sig_rows}
        </tbody>
      </table>
    </div>
  </div>

  <!-- Wallet registry -->
  <div class="section">
    <div class="section-title">🔍 Smart Money Wallet Registry ({len(wallets)} wallets)</div>
    <div class="section-body">
      <table>
        <thead>
          <tr><th>Label</th><th>Address</th><th>Strategy</th><th>Swaps / Early Buys</th><th>Source</th></tr>
        </thead>
        <tbody>
          {wallet_rows}
        </tbody>
      </table>
    </div>
  </div>

  <!-- Analysis -->
  <div class="section">
    <div class="section-title">📋 Full Analysis Report</div>
    <div class="section-body">
      <pre class="analysis-body">SIGNAL VOLUME
━━━━━━━━━━━━
• Total signal lines logged: 67 (as of 2026-02-21)
• HIGH (convergence ≥2 wallets): 4
• MEDIUM (single wallet): ~60
• Scanning period: 2026-02-19 → 2026-02-21 (~2 days)

STRATEGY VERDICT
━━━━━━━━━━━━━━━
Convergence copy trading (HIGH signals):
  • T+1h: 0% win rate, -1.05% avg — slippage eats entry
  • T+4h: 100% win rate, +14.2% avg (HXD +26.1%, WhiteWhale +2.2%)
  → PROMISING but N=2 is statistically meaningless

CRITICAL BUGS (found in analysis)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Signal dedup failure — same signal logged 20x per scan cycle
2. Truncated token addresses — SM_8 signals unbacktestable
3. Wallet label inconsistency — 3 schemas in use (Sol_Bigbrain_, SmartMoney_, SM_)
4. Wallet de-dup for convergence — logs "SM_2,SM_2,...,SM_3" not unique wallets

GO-LIVE ASSESSMENT
━━━━━━━━━━━━━━━━━
NOT YET. Responsibly requires:
  Week 1: Fix signal bugs + collect 15-20 convergence signals
  Week 2: Paper trade dry-run, validate signal→price loop
  Week 3: Live micro-capital ($200-500 USDC), adjust

RISK TABLE
━━━━━━━━━━
  CRITICAL  — Insufficient sample size (N=2)
  HIGH      — Token address logging bug
  HIGH      — No stop-loss logic
  MEDIUM    — MEV/slippage ~1% per round trip
  MEDIUM    — Smart money wallet churn

Analyst: Otto | Data period: 2026-02-19–2026-02-21</pre>
    </div>
    <div class="refresh-note">Page auto-refreshes every 5 minutes. Data live from ~/otto/projects/alpha/</div>
  </div>

</div>
</body>
</html>"""


class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/index.html"):
            self.send_response(404)
            self.end_headers()
            return
        try:
            html = render_html()
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error: {e}".encode())

    def log_message(self, format, *args):
        pass  # suppress access log noise


if __name__ == "__main__":
    os.chdir(Path(__file__).parent)
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        httpd.allow_reuse_address = True
        print(f"[Otto Alpha Dashboard] Serving on http://0.0.0.0:{PORT}", flush=True)
        httpd.serve_forever()
