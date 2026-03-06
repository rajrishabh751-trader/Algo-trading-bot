"""
╔══════════════════════════════════════════════════╗
║   WEB DASHBOARD                                  ║
║   Raat ko analysis daalo, subah results dekho    ║
╚══════════════════════════════════════════════════╝

Phone/Tab ke browser se access karo:
http://your-server:8080

Features:
- Night analysis form (raat ko fill karo)
- Live trade status
- Paper trade history
- Statistics
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
from datetime import datetime
from urllib.parse import parse_qs, urlparse
import config
from strategy_engine import StrategyEngine, NightAnalysis
from paper_trader import PaperTrader
from telegram_bot import TelegramBot

# Global instances
engine = StrategyEngine()
paper_trader = PaperTrader()
telegram = TelegramBot()


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pure Liquidity — Trading Dashboard</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@300;400;600;700;800&display=swap');
  
  :root {
    --bg: #0a0a12;
    --surface: #12121c;
    --surface2: #1a1a28;
    --border: #2a2a40;
    --text: #e8e8f0;
    --dim: #666688;
    --gold: #f0c040;
    --green: #00cc66;
    --red: #ff4444;
    --blue: #4488ff;
    --purple: #aa66ff;
    --cyan: #00ccdd;
  }
  
  * { margin:0; padding:0; box-sizing:border-box; }
  body { 
    background:var(--bg); color:var(--text);
    font-family:'Inter',sans-serif; padding:16px;
    max-width:800px; margin:0 auto;
  }
  
  h1 { color:var(--gold); font-size:24px; margin-bottom:8px; }
  h2 { color:var(--gold); font-size:18px; margin:24px 0 12px; }
  h3 { color:var(--cyan); font-size:14px; margin:16px 0 8px; }
  
  .badge { 
    display:inline-block; padding:4px 12px; border-radius:20px;
    font-size:11px; font-weight:700; letter-spacing:1px;
  }
  .badge-paper { background:rgba(68,136,255,0.15); color:var(--blue); }
  .badge-live { background:rgba(255,68,68,0.15); color:var(--red); }
  
  .card {
    background:var(--surface); border:1px solid var(--border);
    border-radius:12px; padding:20px; margin:12px 0;
  }
  
  .form-group { margin:12px 0; }
  .form-group label {
    display:block; color:var(--dim); font-size:12px;
    font-weight:600; letter-spacing:0.5px; margin-bottom:4px;
  }
  
  input, select, textarea {
    width:100%; padding:10px 14px; border-radius:8px;
    border:1px solid var(--border); background:var(--surface2);
    color:var(--text); font-family:'JetBrains Mono',monospace;
    font-size:14px; outline:none;
  }
  input:focus, select:focus { border-color:var(--gold); }
  select { cursor:pointer; }
  
  .row { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  .row3 { display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; }
  
  .btn {
    display:inline-block; padding:12px 24px; border-radius:8px;
    border:none; font-size:14px; font-weight:700; cursor:pointer;
    font-family:'Inter',sans-serif; width:100%; margin-top:12px;
  }
  .btn-gold { background:var(--gold); color:#000; }
  .btn-gold:hover { background:#e0b030; }
  .btn-green { background:var(--green); color:#000; }
  .btn-red { background:var(--red); color:#fff; }
  
  .switch-row { display:flex; gap:8px; margin:8px 0; }
  .switch-btn {
    flex:1; padding:8px; border-radius:6px; border:1px solid var(--border);
    background:var(--surface2); color:var(--dim); cursor:pointer;
    font-size:12px; font-weight:600; text-align:center;
  }
  .switch-btn.active { border-color:var(--gold); color:var(--gold); background:rgba(240,192,64,0.08); }
  
  .stat-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(100px,1fr)); gap:8px; }
  .stat-box { 
    text-align:center; padding:12px; border-radius:8px;
    background:var(--surface2); border:1px solid var(--border);
  }
  .stat-box .num { font-size:24px; font-weight:800; font-family:'JetBrains Mono',monospace; }
  .stat-box .label { font-size:10px; color:var(--dim); margin-top:4px; }
  
  .trade-item {
    display:flex; justify-content:space-between; align-items:center;
    padding:10px 14px; border-radius:8px; margin:6px 0;
    background:var(--surface2); border:1px solid var(--border);
    font-size:13px;
  }
  .pnl-pos { color:var(--green); font-weight:700; }
  .pnl-neg { color:var(--red); font-weight:700; }
  
  .status-bar {
    display:flex; justify-content:space-between; align-items:center;
    padding:12px 16px; border-radius:8px;
    background:var(--surface2); border:1px solid var(--border);
    margin:8px 0; font-size:13px;
  }
  
  .tabs { display:flex; border-bottom:2px solid var(--border); margin:20px 0 0; }
  .tab {
    padding:10px 20px; cursor:pointer; font-size:13px; font-weight:600;
    color:var(--dim); border-bottom:2px solid transparent; margin-bottom:-2px;
  }
  .tab.active { color:var(--gold); border-bottom-color:var(--gold); }
  
  .tab-content { display:none; }
  .tab-content.active { display:block; }
  
  .alert { padding:12px 16px; border-radius:8px; margin:8px 0; font-size:13px; }
  .alert-success { background:rgba(0,204,102,0.1); border:1px solid rgba(0,204,102,0.3); color:var(--green); }
  .alert-error { background:rgba(255,68,68,0.1); border:1px solid rgba(255,68,68,0.3); color:var(--red); }
  .alert-info { background:rgba(240,192,64,0.1); border:1px solid rgba(240,192,64,0.3); color:var(--gold); }
  
  .disclaimer { text-align:center; color:var(--red); font-size:10px; margin-top:30px; padding:10px; }
  
  @media(max-width:500px) { .row,.row3 { grid-template-columns:1fr; } }
</style>
</head>
<body>

<h1>Pure Liquidity Dashboard</h1>
<div style="display:flex;gap:8px;align-items:center;margin-bottom:16px;">
  <span class="badge badge-paper" id="modeBadge">PAPER MODE</span>
  <span style="color:var(--dim);font-size:12px;" id="timeDisplay"></span>
</div>

<!-- TABS -->
<div class="tabs">
  <div class="tab active" onclick="switchTab('analysis')">Raat Analysis</div>
  <div class="tab" onclick="switchTab('status')">Live Status</div>
  <div class="tab" onclick="switchTab('history')">Trade History</div>
  <div class="tab" onclick="switchTab('stats')">Statistics</div>
</div>

<!-- TAB 1: NIGHT ANALYSIS -->
<div class="tab-content active" id="tab-analysis">
  <div class="card">
    <h3>TREND DIRECTION (Chart se dekho)</h3>
    <div class="row3">
      <div class="form-group">
        <label>1D TREND</label>
        <select id="trend_1d">
          <option value="BEARISH">BEARISH</option>
          <option value="BULLISH">BULLISH</option>
          <option value="SIDEWAYS">SIDEWAYS</option>
        </select>
      </div>
      <div class="form-group">
        <label>4H TREND</label>
        <select id="trend_4h">
          <option value="BEARISH">BEARISH</option>
          <option value="BULLISH">BULLISH</option>
          <option value="SIDEWAYS">SIDEWAYS</option>
        </select>
      </div>
      <div class="form-group">
        <label>1H BIAS</label>
        <select id="bias_1h">
          <option value="NEUTRAL">NEUTRAL</option>
          <option value="BULLISH">BULLISH</option>
          <option value="BEARISH">BEARISH</option>
        </select>
      </div>
    </div>
    
    <h3>LEVELS (Chart se mark karo)</h3>
    <div class="row">
      <div class="form-group">
        <label>MAJOR SSL (Resistance)</label>
        <input type="number" id="major_ssl" placeholder="e.g., 25800" step="10">
      </div>
      <div class="form-group">
        <label>MINOR SSL</label>
        <input type="number" id="minor_ssl" placeholder="e.g., 25400" step="10">
      </div>
    </div>
    <div class="form-group">
      <label>EQ ZONE</label>
      <input type="number" id="eq_zone" placeholder="e.g., 25100" step="10">
    </div>
    <div class="row">
      <div class="form-group">
        <label>MINOR BSL</label>
        <input type="number" id="minor_bsl" placeholder="e.g., 24800" step="10">
      </div>
      <div class="form-group">
        <label>MAJOR BSL (Support)</label>
        <input type="number" id="major_bsl" placeholder="e.g., 24600" step="10">
      </div>
    </div>
    
    <h3>SWEEP STATUS</h3>
    <div class="row">
      <div class="form-group">
        <label>BSL SWEPT? (Neeche ka kaam hua?)</label>
        <div class="switch-row">
          <div class="switch-btn" onclick="toggleSwitch(this,'bsl_swept','YES')">YES</div>
          <div class="switch-btn active" onclick="toggleSwitch(this,'bsl_swept','NO')">NO</div>
        </div>
        <input type="hidden" id="bsl_swept" value="NO">
      </div>
      <div class="form-group">
        <label>SSL SWEPT? (Upar ka kaam hua?)</label>
        <div class="switch-row">
          <div class="switch-btn" onclick="toggleSwitch(this,'ssl_swept','YES')">YES</div>
          <div class="switch-btn active" onclick="toggleSwitch(this,'ssl_swept','NO')">NO</div>
        </div>
        <input type="hidden" id="ssl_swept" value="NO">
      </div>
    </div>
    
    <h3>OI DATA (Dhan se dekho)</h3>
    <div class="row3">
      <div class="form-group">
        <label>MAX CE OI STRIKE</label>
        <input type="number" id="max_ce_oi_strike" placeholder="e.g., 25500" step="50">
      </div>
      <div class="form-group">
        <label>MAX PE OI STRIKE</label>
        <input type="number" id="max_pe_oi_strike" placeholder="e.g., 24500" step="50">
      </div>
      <div class="form-group">
        <label>INDIA VIX</label>
        <input type="number" id="vix" placeholder="e.g., 14.5" step="0.01">
      </div>
    </div>
    
    <h3>OB ZONE (15M se)</h3>
    <div class="row">
      <div class="form-group">
        <label>OB ZONE HIGH</label>
        <input type="number" id="ob_zone_high" placeholder="e.g., 24750" step="10">
      </div>
      <div class="form-group">
        <label>OB ZONE LOW</label>
        <input type="number" id="ob_zone_low" placeholder="e.g., 24700" step="10">
      </div>
    </div>
    
    <h3>NEWS CHECK</h3>
    <div class="form-group">
      <label>RED NEWS EVENT KAL?</label>
      <div class="switch-row">
        <div class="switch-btn" onclick="toggleSwitch(this,'red_news','YES')">YES — No Trade</div>
        <div class="switch-btn active" onclick="toggleSwitch(this,'red_news','NO')">NO — Clear</div>
      </div>
      <input type="hidden" id="red_news" value="NO">
    </div>
    <div class="form-group">
      <label>NEWS NOTES</label>
      <input type="text" id="news_note" placeholder="Koi specific news?">
    </div>
    
    <h3>PREFERRED DIRECTION</h3>
    <div class="switch-row">
      <div class="switch-btn" onclick="toggleSwitch(this,'pref_dir','CE')" style="border-color:rgba(0,204,102,0.3)">CE (Bullish)</div>
      <div class="switch-btn active" onclick="toggleSwitch(this,'pref_dir','NONE')">NONE</div>
      <div class="switch-btn" onclick="toggleSwitch(this,'pref_dir','PE')" style="border-color:rgba(255,68,68,0.3)">PE (Bearish)</div>
    </div>
    <input type="hidden" id="pref_dir" value="NONE">
    
    <h3>CONFIDENCE LEVEL</h3>
    <div class="form-group">
      <label>CONFIDENCE: <span id="confValue" style="color:var(--gold);font-size:18px;">50</span>%</label>
      <input type="range" id="confidence" min="0" max="100" value="50" 
             oninput="document.getElementById('confValue').textContent=this.value"
             style="accent-color:var(--gold);">
    </div>
    
    <h3>SCENARIOS</h3>
    <div class="form-group">
      <label>BULLISH CONDITION (Kab CE lena hai?)</label>
      <input type="text" id="bullish_condition" placeholder="e.g., Green candle + BSL bounce + 24600 hold">
    </div>
    <div class="form-group">
      <label>BEARISH CONDITION (Kab PE lena hai?)</label>
      <input type="text" id="bearish_condition" placeholder="e.g., Red candle + SSL rejection + gap down">
    </div>
    
    <div id="saveAlert"></div>
    <button class="btn btn-gold" onclick="saveAnalysis()">SAVE RAAT KA ANALYSIS</button>
  </div>
</div>

<!-- TAB 2: LIVE STATUS -->
<div class="tab-content" id="tab-status">
  <div class="card">
    <h3>CURRENT STATUS</h3>
    <div class="status-bar">
      <span>Mode</span>
      <span id="statusMode" style="color:var(--blue)">PAPER</span>
    </div>
    <div class="status-bar">
      <span>Active Position</span>
      <span id="statusPosition" style="color:var(--dim)">None</span>
    </div>
    <div class="status-bar">
      <span>Today's Signal</span>
      <span id="statusSignal" style="color:var(--dim)">Waiting...</span>
    </div>
    <div class="status-bar">
      <span>Today's P&L</span>
      <span id="statusPnl">Rs. 0</span>
    </div>
    
    <h3>NIGHT ANALYSIS LOADED</h3>
    <div id="loadedAnalysis" class="alert alert-info">
      Raat ka analysis load ho raha hai...
    </div>
    
    <button class="btn btn-green" onclick="refreshStatus()" style="margin-top:16px;">REFRESH STATUS</button>
  </div>
  
  <!-- MANUAL CANDLE INPUT (for testing) -->
  <div class="card">
    <h3>MANUAL FIRST CANDLE INPUT (Testing)</h3>
    <p style="color:var(--dim);font-size:12px;margin-bottom:12px;">
      Paper trading test karne ke liye manually candle data daalo
    </p>
    <div class="row">
      <div class="form-group">
        <label>OPEN</label>
        <input type="number" id="candle_open" placeholder="24850" step="1">
      </div>
      <div class="form-group">
        <label>HIGH</label>
        <input type="number" id="candle_high" placeholder="24900" step="1">
      </div>
    </div>
    <div class="row">
      <div class="form-group">
        <label>LOW</label>
        <input type="number" id="candle_low" placeholder="24810" step="1">
      </div>
      <div class="form-group">
        <label>CLOSE</label>
        <input type="number" id="candle_close" placeholder="24880" step="1">
      </div>
    </div>
    <button class="btn btn-gold" onclick="testCandle()">TEST FIRST CANDLE</button>
    <div id="candleResult"></div>
  </div>
  
  <!-- MANUAL PRICE UPDATE (for testing exits) -->
  <div class="card">
    <h3>MANUAL PRICE UPDATE (Test Exits)</h3>
    <div class="row">
      <div class="form-group">
        <label>CURRENT NIFTY</label>
        <input type="number" id="update_nifty" placeholder="24900" step="1">
      </div>
      <div class="form-group">
        <label>CURRENT TIME (HH:MM)</label>
        <input type="text" id="update_time" placeholder="09:45" value="">
      </div>
    </div>
    <button class="btn btn-green" onclick="testPriceUpdate()">CHECK EXIT CONDITIONS</button>
    <div id="exitResult"></div>
  </div>
</div>

<!-- TAB 3: HISTORY -->
<div class="tab-content" id="tab-history">
  <div class="card">
    <h3>PAPER TRADE HISTORY</h3>
    <div id="tradeHistory">Loading...</div>
  </div>
</div>

<!-- TAB 4: STATS -->
<div class="tab-content" id="tab-stats">
  <div class="card">
    <h3>OVERALL STATISTICS</h3>
    <div id="statsGrid" class="stat-grid">Loading...</div>
  </div>
</div>

<div class="disclaimer">
  ⚠️ EDUCATIONAL ONLY — Trading involves risk. No guaranteed profit. Paper mode = no real money.
</div>

<script>
  // Tab switching
  function switchTab(name) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
    document.getElementById('tab-' + name).classList.add('active');
    
    if (name === 'history') loadHistory();
    if (name === 'stats') loadStats();
    if (name === 'status') refreshStatus();
  }
  
  // Toggle switches
  function toggleSwitch(el, inputId, value) {
    el.parentElement.querySelectorAll('.switch-btn').forEach(b => b.classList.remove('active'));
    el.classList.add('active');
    document.getElementById(inputId).value = value;
  }
  
  // Save night analysis
  function saveAnalysis() {
    const data = {
      date: new Date().toISOString().split('T')[0],
      trend_1d: document.getElementById('trend_1d').value,
      trend_4h: document.getElementById('trend_4h').value,
      bias_1h: document.getElementById('bias_1h').value,
      major_ssl: parseFloat(document.getElementById('major_ssl').value) || 0,
      minor_ssl: parseFloat(document.getElementById('minor_ssl').value) || 0,
      eq_zone: parseFloat(document.getElementById('eq_zone').value) || 0,
      minor_bsl: parseFloat(document.getElementById('minor_bsl').value) || 0,
      major_bsl: parseFloat(document.getElementById('major_bsl').value) || 0,
      bsl_swept: document.getElementById('bsl_swept').value === 'YES',
      ssl_swept: document.getElementById('ssl_swept').value === 'YES',
      max_ce_oi_strike: parseFloat(document.getElementById('max_ce_oi_strike').value) || 0,
      max_pe_oi_strike: parseFloat(document.getElementById('max_pe_oi_strike').value) || 0,
      vix: parseFloat(document.getElementById('vix').value) || 15,
      ob_zone_high: parseFloat(document.getElementById('ob_zone_high').value) || 0,
      ob_zone_low: parseFloat(document.getElementById('ob_zone_low').value) || 0,
      red_news_event: document.getElementById('red_news').value === 'YES',
      news_note: document.getElementById('news_note').value,
      preferred_direction: document.getElementById('pref_dir').value,
      confidence: parseInt(document.getElementById('confidence').value),
      bullish_condition: document.getElementById('bullish_condition').value,
      bearish_condition: document.getElementById('bearish_condition').value,
    };
    
    fetch('/api/save-analysis', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    })
    .then(r => r.json())
    .then(d => {
      const el = document.getElementById('saveAlert');
      if (d.status === 'ok') {
        el.innerHTML = '<div class="alert alert-success">Analysis saved! Telegram pe bhi bhej diya. Ab so jao! 😴</div>';
      } else {
        el.innerHTML = '<div class="alert alert-error">Error: ' + (d.error || 'Unknown') + '</div>';
      }
    })
    .catch(e => {
      document.getElementById('saveAlert').innerHTML = '<div class="alert alert-error">Network error: ' + e + '</div>';
    });
  }
  
  // Test first candle
  function testCandle() {
    const data = {
      open: parseFloat(document.getElementById('candle_open').value),
      high: parseFloat(document.getElementById('candle_high').value),
      low: parseFloat(document.getElementById('candle_low').value),
      close: parseFloat(document.getElementById('candle_close').value),
      volume: 50000,
      timestamp: new Date().toISOString()
    };
    
    if (!data.open || !data.high || !data.low || !data.close) {
      document.getElementById('candleResult').innerHTML = '<div class="alert alert-error">Sab fields fill karo!</div>';
      return;
    }
    
    fetch('/api/test-candle', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    })
    .then(r => r.json())
    .then(d => {
      const el = document.getElementById('candleResult');
      if (d.signal) {
        const action = d.signal.action;
        const cls = action.includes('BUY') ? 'alert-success' : 'alert-info';
        let html = '<div class="alert ' + cls + '">';
        html += '<strong>' + action + '</strong><br>';
        if (d.signal.strike) html += 'Strike: ' + d.signal.strike + ' ' + d.signal.option_type + '<br>';
        if (d.signal.sl_nifty) html += 'SL: ' + d.signal.sl_nifty + '<br>';
        if (d.signal.tp1_nifty) html += 'TP1: ' + d.signal.tp1_nifty + '<br>';
        if (d.signal.tp2_nifty) html += 'TP2: ' + d.signal.tp2_nifty + '<br>';
        html += 'Confidence: ' + d.signal.confidence + '%<br>';
        if (d.signal.skip_reasons && d.signal.skip_reasons.length) {
          html += '<br>Skip reasons:<br>' + d.signal.skip_reasons.join('<br>');
        }
        html += '</div>';
        el.innerHTML = html;
      }
    })
    .catch(e => {
      document.getElementById('candleResult').innerHTML = '<div class="alert alert-error">' + e + '</div>';
    });
  }
  
  // Test price update
  function testPriceUpdate() {
    const data = {
      nifty: parseFloat(document.getElementById('update_nifty').value),
      time: document.getElementById('update_time').value
    };
    
    fetch('/api/update-price', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    })
    .then(r => r.json())
    .then(d => {
      const el = document.getElementById('exitResult');
      if (d.exit) {
        const cls = d.exit.action === 'FULL_EXIT' ? 'alert-error' : 'alert-success';
        el.innerHTML = '<div class="alert ' + cls + '">' + d.exit.message + '</div>';
      } else {
        el.innerHTML = '<div class="alert alert-info">HOLD — No exit condition met.</div>';
      }
    });
  }
  
  // Load history
  function loadHistory() {
    fetch('/api/history')
    .then(r => r.json())
    .then(trades => {
      const el = document.getElementById('tradeHistory');
      if (!trades.length) { el.innerHTML = '<p style="color:var(--dim)">Abhi koi trade nahi hua.</p>'; return; }
      let html = '';
      trades.reverse().forEach(t => {
        const pnlClass = t.pnl > 0 ? 'pnl-pos' : t.pnl < 0 ? 'pnl-neg' : '';
        html += '<div class="trade-item">';
        html += '<div><strong>' + t.date + '</strong><br><span style="color:var(--dim);font-size:11px;">' + t.type + ' | ' + t.exit_reason + '</span></div>';
        html += '<div class="' + pnlClass + '">Rs. ' + (t.pnl > 0 ? '+' : '') + t.pnl.toFixed(0) + '</div>';
        html += '</div>';
      });
      el.innerHTML = html;
    });
  }
  
  // Load stats
  function loadStats() {
    fetch('/api/stats')
    .then(r => r.json())
    .then(s => {
      const el = document.getElementById('statsGrid');
      const pnlColor = s.total_pnl >= 0 ? 'var(--green)' : 'var(--red)';
      el.innerHTML = `
        <div class="stat-box"><div class="num">${s.total_trades}</div><div class="label">TOTAL TRADES</div></div>
        <div class="stat-box"><div class="num" style="color:var(--green)">${s.wins || 0}</div><div class="label">WINS</div></div>
        <div class="stat-box"><div class="num" style="color:var(--red)">${s.losses || 0}</div><div class="label">LOSSES</div></div>
        <div class="stat-box"><div class="num" style="color:var(--gold)">${s.win_rate || 0}%</div><div class="label">WIN RATE</div></div>
        <div class="stat-box"><div class="num" style="color:${pnlColor}">Rs.${(s.total_pnl || 0).toFixed(0)}</div><div class="label">TOTAL P&L</div></div>
        <div class="stat-box"><div class="num">${s.current_streak || 'N/A'}</div><div class="label">STREAK</div></div>
      `;
    });
  }
  
  // Refresh status
  function refreshStatus() {
    fetch('/api/status')
    .then(r => r.json())
    .then(d => {
      document.getElementById('statusMode').textContent = d.mode || 'PAPER';
      document.getElementById('statusPosition').textContent = d.position || 'None';
      document.getElementById('statusSignal').textContent = d.signal || 'Waiting...';
      
      const pnl = d.today_pnl || 0;
      const pnlEl = document.getElementById('statusPnl');
      pnlEl.textContent = 'Rs. ' + (pnl >= 0 ? '+' : '') + pnl.toFixed(0);
      pnlEl.style.color = pnl >= 0 ? 'var(--green)' : 'var(--red)';
      
      if (d.analysis) {
        document.getElementById('loadedAnalysis').innerHTML = 
          `<strong>Date:</strong> ${d.analysis.date || 'N/A'} | 
           <strong>Trends:</strong> 1D=${d.analysis.trend_1d} 4H=${d.analysis.trend_4h} | 
           <strong>VIX:</strong> ${d.analysis.vix} | 
           <strong>Conf:</strong> ${d.analysis.confidence}%`;
      }
    });
  }
  
  // Time display
  setInterval(() => {
    const now = new Date();
    document.getElementById('timeDisplay').textContent = now.toLocaleTimeString('en-IN');
  }, 1000);
  
  // Load status on page load
  refreshStatus();
</script>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for Dashboard"""
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass
    
    def _send_response(self, code, content_type, data):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        if isinstance(data, str):
            self.wfile.write(data.encode('utf-8'))
        else:
            self.wfile.write(data)
    
    def do_OPTIONS(self):
        self._send_response(200, 'text/plain', '')
    
    def do_GET(self):
        path = urlparse(self.path).path
        
        if path == '/' or path == '/dashboard':
            self._send_response(200, 'text/html', DASHBOARD_HTML)
        
        elif path == '/api/status':
            analysis = engine.get_night_analysis()
            signal = engine.current_signal
            position = paper_trader.active_position
            
            status = {
                "mode": config.TRADING_MODE,
                "analysis": analysis.to_dict() if analysis else None,
                "signal": signal.action if signal else "Waiting...",
                "position": f"{position.option_type} @ {position.strike}" if position else "None",
                "today_pnl": paper_trader.today_pnl
            }
            self._send_response(200, 'application/json', json.dumps(status))
        
        elif path == '/api/history':
            self._send_response(200, 'application/json', json.dumps(paper_trader.paper_trades))
        
        elif path == '/api/stats':
            stats = paper_trader.get_stats()
            self._send_response(200, 'application/json', json.dumps(stats))
        
        else:
            self._send_response(404, 'text/plain', 'Not found')
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_response(400, 'application/json', json.dumps({"error": "Invalid JSON"}))
            return
        
        path = urlparse(self.path).path
        
        if path == '/api/save-analysis':
            try:
                engine.load_night_analysis(data)
                telegram.send_night_analysis_saved(data)
                self._send_response(200, 'application/json', json.dumps({"status": "ok"}))
            except Exception as e:
                self._send_response(500, 'application/json', json.dumps({"error": str(e)}))
        
        elif path == '/api/test-candle':
            try:
                result = paper_trader.process_first_candle(data)
                self._send_response(200, 'application/json', json.dumps(result))
            except Exception as e:
                self._send_response(500, 'application/json', json.dumps({"error": str(e)}))
        
        elif path == '/api/update-price':
            try:
                exit_result = paper_trader.update_price(
                    data.get("nifty", 0),
                    data.get("time", "")
                )
                self._send_response(200, 'application/json', json.dumps({
                    "exit": exit_result
                }))
            except Exception as e:
                self._send_response(500, 'application/json', json.dumps({"error": str(e)}))
        
        elif path == '/api/reset':
            paper_trader.reset_daily()
            self._send_response(200, 'application/json', json.dumps({"status": "reset done"}))
        
        else:
            self._send_response(404, 'application/json', json.dumps({"error": "Not found"}))


def start_dashboard():
    """Start the web dashboard"""
    server = HTTPServer(
        (config.DASHBOARD_HOST, config.DASHBOARD_PORT), 
        DashboardHandler
    )
    print(f"""
╔══════════════════════════════════════════════════╗
║   PURE LIQUIDITY — TRADING DASHBOARD             ║
║                                                  ║
║   Dashboard: http://localhost:{config.DASHBOARD_PORT}              ║
║   Mode: {config.TRADING_MODE}                              ║
║                                                  ║
║   Browser mein kholo aur analysis daalo!         ║
╚══════════════════════════════════════════════════╝
    """)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
        server.server_close()


if __name__ == "__main__":
    start_dashboard()
