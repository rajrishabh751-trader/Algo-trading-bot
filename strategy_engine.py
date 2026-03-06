"""
╔══════════════════════════════════════════════════╗
║   PURE LIQUIDITY — STRATEGY ENGINE               ║
║   Core logic for trade decisions                 ║
╚══════════════════════════════════════════════════╝

Yeh file mein POORI strategy coded hai:
- First candle analysis
- Body % check
- Direction decision (CE/PE/SKIP)
- SL/TP calculation
- Confidence scoring
- All iron rules
"""

import json
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional, List
from enum import Enum
import config


class Direction(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class TradeAction(str, Enum):
    BUY_CE = "BUY_CE"
    BUY_PE = "BUY_PE"
    NO_TRADE = "NO_TRADE"
    SKIP = "SKIP"


class ExitReason(str, Enum):
    TP1_HIT = "TP1_HIT"
    TP2_HIT = "TP2_HIT"
    SL_HIT = "SL_HIT"
    TIME_EXIT = "TIME_EXIT_1030"
    MANUAL = "MANUAL"


@dataclass
class Candle:
    """5-minute candle data"""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int = 0

    @property
    def is_green(self) -> bool:
        return self.close > self.open

    @property
    def is_red(self) -> bool:
        return self.close < self.open

    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)

    @property
    def total_size(self) -> float:
        return self.high - self.low

    @property
    def body_percent(self) -> float:
        if self.total_size == 0:
            return 0
        return (self.body_size / self.total_size) * 100

    @property
    def is_doji(self) -> bool:
        return self.body_percent < 20

    @property
    def is_strong(self) -> bool:
        """Body 50%+ of total candle = Strong"""
        return self.body_percent >= config.MIN_BODY_PERCENT

    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low


@dataclass
class NightAnalysis:
    """Raat ka analysis — tu dashboard se fill karega"""
    date: str                              # Analysis date
    
    # Trend data (1D + 4H + 1H)
    trend_1d: str = "BEARISH"              # BULLISH / BEARISH / SIDEWAYS
    trend_4h: str = "BEARISH"              # BULLISH / BEARISH / SIDEWAYS
    bias_1h: str = "NEUTRAL"               # BULLISH / BEARISH / NEUTRAL
    
    # Levels
    major_ssl: float = 0                   # Major resistance (1D)
    minor_ssl: float = 0                   # Minor resistance
    eq_zone: float = 0                     # Equilibrium
    minor_bsl: float = 0                   # Minor support
    major_bsl: float = 0                   # Major support (1D)
    
    # Sweep status
    bsl_swept: bool = False                # BSL swept? → LONG only
    ssl_swept: bool = False                # SSL swept? → SHORT only
    
    # OI data
    max_ce_oi_strike: float = 0            # Max CE OI = SSL confirm
    max_pe_oi_strike: float = 0            # Max PE OI = BSL confirm
    
    # VIX
    vix: float = 15.0                      # India VIX value
    
    # OB Zone (from 15M)
    ob_zone_high: float = 0               
    ob_zone_low: float = 0
    
    # News
    red_news_event: bool = False           # Any red event tomorrow?
    news_note: str = ""                    # Notes about news
    
    # Scenarios
    bullish_condition: str = ""            # When to take CE
    bearish_condition: str = ""            # When to take PE
    
    # Preferred direction (from analysis)
    preferred_direction: str = "NONE"      # CE / PE / NONE
    
    # Confidence
    confidence: int = 50                   # 0-100%
    
    @property
    def trends_aligned(self) -> bool:
        """Check if all timeframes agree"""
        return (self.trend_1d == self.trend_4h and 
                self.trend_4h == self.bias_1h and
                self.trend_1d != "SIDEWAYS")
    
    @property
    def all_bearish(self) -> bool:
        return self.trend_1d == "BEARISH" and self.trend_4h == "BEARISH"
    
    @property
    def all_bullish(self) -> bool:
        return self.trend_1d == "BULLISH" and self.trend_4h == "BULLISH"

    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data):
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class TradeSignal:
    """Generated trade signal"""
    timestamp: str
    action: str                    # BUY_CE / BUY_PE / NO_TRADE / SKIP
    strike: float = 0             # ATM strike price
    option_type: str = ""         # CE or PE
    entry_price_nifty: float = 0  # Nifty level at entry
    sl_nifty: float = 0          # SL in Nifty points
    tp1_nifty: float = 0         # TP1 in Nifty points
    tp2_nifty: float = 0         # TP2 in Nifty points
    confidence: int = 0           # Confidence %
    reasons: list = field(default_factory=list)  # Why this decision
    skip_reasons: list = field(default_factory=list)  # Why skip/no trade

    def to_dict(self):
        return asdict(self)


@dataclass
class TradeRecord:
    """Trade execution record"""
    date: str
    signal: dict
    entry_time: str = ""
    exit_time: str = ""
    entry_price: float = 0       # Option premium at entry
    exit_price: float = 0        # Option premium at exit
    quantity: int = 0
    pnl: float = 0
    exit_reason: str = ""
    notes: str = ""
    
    def to_dict(self):
        return asdict(self)


class StrategyEngine:
    """
    Pure Liquidity + Operator Following Strategy Engine
    
    Yeh class POORI strategy handle karti hai:
    1. Night analysis load karo
    2. First candle analyze karo
    3. Trade signal generate karo
    4. SL/TP calculate karo
    5. Exit conditions check karo
    """
    
    def __init__(self):
        self.night_analysis: Optional[NightAnalysis] = None
        self.first_candle: Optional[Candle] = None
        self.current_signal: Optional[TradeSignal] = None
        self.today_trades: int = 0
        self.trade_log: List[TradeRecord] = []
        
        # Ensure data directory exists
        os.makedirs(config.DATA_DIR, exist_ok=True)
    
    # ═══════════════════════════════════════════
    # NIGHT ANALYSIS
    # ═══════════════════════════════════════════
    
    def load_night_analysis(self, data: dict) -> NightAnalysis:
        """Dashboard se aaya hua raat ka analysis load karo"""
        self.night_analysis = NightAnalysis.from_dict(data)
        
        # Save to file
        with open(config.NIGHT_ANALYSIS_FILE, 'w') as f:
            json.dump(self.night_analysis.to_dict(), f, indent=2)
        
        return self.night_analysis
    
    def get_night_analysis(self) -> Optional[NightAnalysis]:
        """Saved night analysis load karo"""
        if self.night_analysis:
            return self.night_analysis
        
        try:
            with open(config.NIGHT_ANALYSIS_FILE, 'r') as f:
                data = json.load(f)
                self.night_analysis = NightAnalysis.from_dict(data)
                return self.night_analysis
        except (FileNotFoundError, json.JSONDecodeError):
            return None
    
    # ═══════════════════════════════════════════
    # PRE-TRADE CHECKS
    # ═══════════════════════════════════════════
    
    def pre_trade_checks(self) -> tuple:
        """
        Sab iron rules check karo PEHLE trade se
        Returns: (can_trade: bool, reasons: list)
        """
        analysis = self.get_night_analysis()
        reasons = []
        can_trade = True
        
        if not analysis:
            return False, ["Night analysis nahi mila! Pehle raat ka homework karo."]
        
        # Check 1: Max trades per day
        if self.today_trades >= config.MAX_TRADES_PER_DAY:
            reasons.append(f"Already {self.today_trades} trade(s) today. Max = {config.MAX_TRADES_PER_DAY}. BAND KARO.")
            can_trade = False
        
        # Check 2: VIX
        if analysis.vix >= config.VIX_NO_TRADE:
            reasons.append(f"VIX = {analysis.vix} (>= {config.VIX_NO_TRADE}). TOO HIGH. NO TRADE!")
            can_trade = False
        elif analysis.vix >= config.VIX_GREEN:
            reasons.append(f"VIX = {analysis.vix} (>= {config.VIX_GREEN}). CAUTION — premium expensive.")
        
        # Check 3: Red news event
        if analysis.red_news_event:
            reasons.append(f"RED NEWS EVENT: {analysis.news_note}. NO TRADE!")
            can_trade = False
        
        # Check 4: Confidence
        if analysis.confidence < config.CONFIDENCE_NO_TRADE:
            reasons.append(f"Confidence = {analysis.confidence}% (< {config.CONFIDENCE_NO_TRADE}%). NO TRADE!")
            can_trade = False
        
        # Check 5: Trends aligned?
        if not analysis.trends_aligned:
            reasons.append(f"Trends NOT aligned: 1D={analysis.trend_1d}, 4H={analysis.trend_4h}, 1H={analysis.bias_1h}. WEAK setup.")
        
        if can_trade:
            reasons.append("Pre-trade checks PASSED. Waiting for first candle...")
        
        return can_trade, reasons
    
    # ═══════════════════════════════════════════
    # FIRST CANDLE ANALYSIS
    # ═══════════════════════════════════════════
    
    def analyze_first_candle(self, candle: Candle) -> TradeSignal:
        """
        PEHLI 5M CANDLE (9:15-9:20) analyze karo
        Yeh MAIN DECISION FUNCTION hai!
        
        Returns: TradeSignal with action + SL + TP
        """
        self.first_candle = candle
        analysis = self.get_night_analysis()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        signal = TradeSignal(timestamp=now, action=TradeAction.NO_TRADE.value)
        
        # ─── STEP 1: Pre-trade checks ───
        can_trade, pre_reasons = self.pre_trade_checks()
        signal.reasons.extend(pre_reasons)
        
        if not can_trade:
            signal.action = TradeAction.NO_TRADE.value
            signal.skip_reasons = [r for r in pre_reasons if "NO TRADE" in r]
            self.current_signal = signal
            return signal
        
        # ─── STEP 2: Candle analysis ───
        signal.reasons.append(f"Pehli candle: O={candle.open} H={candle.high} L={candle.low} C={candle.close}")
        signal.reasons.append(f"Body: {candle.body_percent:.1f}% | {'GREEN' if candle.is_green else 'RED'}")
        
        # Check: Doji = SKIP
        if candle.is_doji:
            signal.action = TradeAction.SKIP.value
            signal.skip_reasons.append(f"DOJI candle (body {candle.body_percent:.1f}%). No direction. SKIP!")
            self.current_signal = signal
            return signal
        
        # Check: Body < 50% = SKIP
        if not candle.is_strong:
            signal.action = TradeAction.SKIP.value
            signal.skip_reasons.append(
                f"Weak candle — body {candle.body_percent:.1f}% (need {config.MIN_BODY_PERCENT}%+). SKIP!"
            )
            self.current_signal = signal
            return signal
        
        # ─── STEP 3: Direction decision ───
        candle_direction = Direction.BULLISH if candle.is_green else Direction.BEARISH
        signal.reasons.append(f"Candle direction: {candle_direction.value}")
        
        # ─── STEP 4: Sweep rule check ───
        if analysis.bsl_swept and candle_direction == Direction.BEARISH:
            signal.action = TradeAction.NO_TRADE.value
            signal.skip_reasons.append(
                "BSL already SWEPT — SHORT (PE) mat lo! Sweep direction mein trade nahi."
            )
            self.current_signal = signal
            return signal
        
        if analysis.ssl_swept and candle_direction == Direction.BULLISH:
            signal.action = TradeAction.NO_TRADE.value
            signal.skip_reasons.append(
                "SSL already SWEPT — LONG (CE) mat lo! Sweep direction mein trade nahi."
            )
            self.current_signal = signal
            return signal
        
        # ─── STEP 5: Higher TF alignment check ───
        if candle_direction == Direction.BULLISH and analysis.all_bearish:
            signal.action = TradeAction.NO_TRADE.value
            signal.skip_reasons.append(
                "CONFLICT: Candle GREEN but 1D + 4H BEARISH. Higher TF wins! NO CE!"
            )
            self.current_signal = signal
            return signal
        
        if candle_direction == Direction.BEARISH and analysis.all_bullish:
            signal.action = TradeAction.NO_TRADE.value
            signal.skip_reasons.append(
                "CONFLICT: Candle RED but 1D + 4H BULLISH. Higher TF wins! NO PE!"
            )
            self.current_signal = signal
            return signal
        
        # ─── STEP 6: BSL/SSL zone alignment ───
        zone_aligned = False
        if candle_direction == Direction.BULLISH:
            # For CE: Price should be near BSL zone (support bounce)
            if analysis.major_bsl > 0 and candle.low <= analysis.minor_bsl * 1.005:
                zone_aligned = True
                signal.reasons.append(f"Price near BSL zone ({analysis.minor_bsl}). Zone aligned for CE!")
            elif analysis.bsl_swept:
                zone_aligned = True
                signal.reasons.append("BSL swept + GREEN candle = Operator long. Zone aligned!")
        else:
            # For PE: Price should be near SSL zone (resistance rejection)
            if analysis.major_ssl > 0 and candle.high >= analysis.minor_ssl * 0.995:
                zone_aligned = True
                signal.reasons.append(f"Price near SSL zone ({analysis.minor_ssl}). Zone aligned for PE!")
            elif analysis.ssl_swept:
                zone_aligned = True
                signal.reasons.append("SSL swept + RED candle = Operator short. Zone aligned!")
        
        # ─── STEP 7: Calculate confidence ───
        confidence = self._calculate_confidence(candle, analysis, candle_direction, zone_aligned)
        signal.confidence = confidence
        signal.reasons.append(f"Calculated confidence: {confidence}%")
        
        # ─── STEP 8: Final decision ───
        if confidence < config.CONFIDENCE_NO_TRADE:
            signal.action = TradeAction.SKIP.value
            signal.skip_reasons.append(f"Confidence {confidence}% < {config.CONFIDENCE_NO_TRADE}%. SKIP!")
            self.current_signal = signal
            return signal
        
        # ── TRADE CONFIRMED! ──
        if candle_direction == Direction.BULLISH:
            signal.action = TradeAction.BUY_CE.value
            signal.option_type = config.OPTION_TYPE_CE
        else:
            signal.action = TradeAction.BUY_PE.value
            signal.option_type = config.OPTION_TYPE_PE
        
        # ─── STEP 9: Calculate strike, SL, TP ───
        signal.entry_price_nifty = candle.close
        signal.strike = self._get_atm_strike(candle.close)
        
        if signal.option_type == config.OPTION_TYPE_CE:
            signal.sl_nifty = candle.low - config.SL_BUFFER_POINTS
            signal.tp1_nifty = candle.close + config.TP1_POINTS
            signal.tp2_nifty = candle.close + config.TP2_POINTS
        else:
            signal.sl_nifty = candle.high + config.SL_BUFFER_POINTS
            signal.tp1_nifty = candle.close - config.TP1_POINTS
            signal.tp2_nifty = candle.close - config.TP2_POINTS
        
        signal.reasons.append(
            f"TRADE: {signal.option_type} | Strike: {signal.strike} | "
            f"SL: {signal.sl_nifty} | TP1: {signal.tp1_nifty} | TP2: {signal.tp2_nifty}"
        )
        
        self.current_signal = signal
        return signal
    
    # ═══════════════════════════════════════════
    # CONFIDENCE CALCULATOR
    # ═══════════════════════════════════════════
    
    def _calculate_confidence(self, candle: Candle, analysis: NightAnalysis, 
                              direction: Direction, zone_aligned: bool) -> int:
        """
        Confidence score calculate karo (0-100%)
        
        Scoring:
        - TF alignment:     +25 points
        - Candle strength:   +20 points
        - Zone alignment:    +15 points
        - VIX favorable:     +15 points
        - Sweep support:     +10 points
        - OI alignment:      +10 points
        - Night confidence:  +5 points
        Total possible:      100 points
        """
        score = 0
        
        # 1. Timeframe alignment (25 pts)
        if analysis.trends_aligned:
            score += 25
        elif (direction == Direction.BULLISH and analysis.trend_1d == "BULLISH") or \
             (direction == Direction.BEARISH and analysis.trend_1d == "BEARISH"):
            score += 15  # At least 1D matches
        elif (direction == Direction.BULLISH and analysis.trend_4h == "BULLISH") or \
             (direction == Direction.BEARISH and analysis.trend_4h == "BEARISH"):
            score += 10  # At least 4H matches
        
        # 2. Candle strength (20 pts)
        if candle.body_percent >= 70:
            score += 20   # Very strong candle
        elif candle.body_percent >= 60:
            score += 15
        elif candle.body_percent >= 50:
            score += 10
        
        # 3. Zone alignment (15 pts)
        if zone_aligned:
            score += 15
        
        # 4. VIX (15 pts)
        if analysis.vix < 13:
            score += 15   # Very low VIX = great
        elif analysis.vix < config.VIX_GREEN:
            score += 12
        elif analysis.vix < 18:
            score += 5
        # Above 18 = 0 points
        
        # 5. Sweep support (10 pts)
        if direction == Direction.BULLISH and analysis.bsl_swept:
            score += 10   # BSL swept + going long = perfect
        elif direction == Direction.BEARISH and analysis.ssl_swept:
            score += 10   # SSL swept + going short = perfect
        
        # 6. OI alignment (10 pts)
        if analysis.max_ce_oi_strike > 0 and analysis.max_pe_oi_strike > 0:
            if direction == Direction.BULLISH and candle.close < analysis.max_ce_oi_strike:
                score += 10  # Room to move up
            elif direction == Direction.BEARISH and candle.close > analysis.max_pe_oi_strike:
                score += 10  # Room to move down
            else:
                score += 3
        
        # 7. Night analysis confidence boost (5 pts)
        if analysis.confidence >= 80:
            score += 5
        elif analysis.confidence >= 70:
            score += 3
        
        return min(score, 100)
    
    # ═══════════════════════════════════════════
    # EXIT CONDITIONS
    # ═══════════════════════════════════════════
    
    def check_exit_conditions(self, current_nifty: float, current_time: str) -> Optional[dict]:
        """
        Har tick pe check karo — exit karna hai ya nahi?
        
        Returns: {action: "EXIT"/"PARTIAL_EXIT"/"HOLD", reason: str} or None
        """
        if not self.current_signal or self.current_signal.action in [
            TradeAction.NO_TRADE.value, TradeAction.SKIP.value
        ]:
            return None
        
        signal = self.current_signal
        
        # Check 1: 10:30 AM HARD EXIT
        try:
            time_parts = current_time.split(":")
            hour, minute = int(time_parts[0]), int(time_parts[1])
            if hour > 10 or (hour == 10 and minute >= 30):
                return {
                    "action": "EXIT_ALL",
                    "reason": "10:30 AM — HARD EXIT! NO EXCEPTION!",
                    "exit_type": ExitReason.TIME_EXIT.value
                }
        except (ValueError, IndexError):
            pass
        
        is_ce = signal.option_type == config.OPTION_TYPE_CE
        
        # Check 2: SL Hit
        if is_ce and current_nifty <= signal.sl_nifty:
            return {
                "action": "EXIT_ALL",
                "reason": f"SL HIT! Nifty = {current_nifty} <= SL {signal.sl_nifty}. EXIT!",
                "exit_type": ExitReason.SL_HIT.value
            }
        elif not is_ce and current_nifty >= signal.sl_nifty:
            return {
                "action": "EXIT_ALL",
                "reason": f"SL HIT! Nifty = {current_nifty} >= SL {signal.sl_nifty}. EXIT!",
                "exit_type": ExitReason.SL_HIT.value
            }
        
        # Check 3: TP2 Hit (exit all remaining)
        if is_ce and current_nifty >= signal.tp2_nifty:
            return {
                "action": "EXIT_ALL",
                "reason": f"TP2 HIT! Nifty = {current_nifty} >= TP2 {signal.tp2_nifty}. FULL EXIT!",
                "exit_type": ExitReason.TP2_HIT.value
            }
        elif not is_ce and current_nifty <= signal.tp2_nifty:
            return {
                "action": "EXIT_ALL",
                "reason": f"TP2 HIT! Nifty = {current_nifty} <= TP2 {signal.tp2_nifty}. FULL EXIT!",
                "exit_type": ExitReason.TP2_HIT.value
            }
        
        # Check 4: TP1 Hit (partial exit 50%)
        if is_ce and current_nifty >= signal.tp1_nifty:
            return {
                "action": "PARTIAL_EXIT",
                "reason": f"TP1 HIT! Nifty = {current_nifty} >= TP1 {signal.tp1_nifty}. 50% EXIT! Move SL to breakeven.",
                "exit_type": ExitReason.TP1_HIT.value,
                "exit_percent": config.TP1_EXIT_PERCENT
            }
        elif not is_ce and current_nifty <= signal.tp1_nifty:
            return {
                "action": "PARTIAL_EXIT",
                "reason": f"TP1 HIT! Nifty = {current_nifty} <= TP1 {signal.tp1_nifty}. 50% EXIT! Move SL to breakeven.",
                "exit_type": ExitReason.TP1_HIT.value,
                "exit_percent": config.TP1_EXIT_PERCENT
            }
        
        # No exit condition met
        return None
    
    # ═══════════════════════════════════════════
    # GAP ANALYSIS
    # ═══════════════════════════════════════════
    
    def analyze_gap(self, prev_close: float, open_price: float) -> dict:
        """
        Gap analysis at market open
        """
        gap = open_price - prev_close
        gap_pct = (gap / prev_close) * 100
        
        if abs(gap) >= config.GAP_THRESHOLD:
            if gap > 0:
                gap_type = "GAP_UP"
                note = f"Gap UP {gap:.0f} pts ({gap_pct:.2f}%). SSL zone watch → Rejection = PE"
            else:
                gap_type = "GAP_DOWN"
                note = f"Gap DOWN {abs(gap):.0f} pts ({gap_pct:.2f}%). BSL zone watch → Bounce = CE"
        else:
            gap_type = "FLAT"
            note = f"Flat open ({gap:.0f} pts). Wait for first candle direction."
        
        return {
            "gap_type": gap_type,
            "gap_points": gap,
            "gap_percent": gap_pct,
            "note": note
        }
    
    # ═══════════════════════════════════════════
    # HELPER FUNCTIONS
    # ═══════════════════════════════════════════
    
    def _get_atm_strike(self, nifty_price: float) -> float:
        """Get nearest ATM strike (Nifty strikes are in 50 intervals)"""
        return round(nifty_price / 50) * 50
    
    def reset_daily(self):
        """Reset for new trading day"""
        self.first_candle = None
        self.current_signal = None
        self.today_trades = 0
    
    # ═══════════════════════════════════════════
    # TRADE LOGGING
    # ═══════════════════════════════════════════
    
    def log_trade(self, record: TradeRecord):
        """Trade record save karo"""
        self.trade_log.append(record)
        self.today_trades += 1
        
        # Save to file
        try:
            existing = []
            if os.path.exists(config.TRADE_LOG_FILE):
                with open(config.TRADE_LOG_FILE, 'r') as f:
                    existing = json.load(f)
            existing.append(record.to_dict())
            with open(config.TRADE_LOG_FILE, 'w') as f:
                json.dump(existing, f, indent=2)
        except Exception as e:
            print(f"Error saving trade log: {e}")
    
    def get_trade_history(self) -> list:
        """Trade history load karo"""
        try:
            with open(config.TRADE_LOG_FILE, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    # ═══════════════════════════════════════════
    # SIGNAL SUMMARY (for Telegram)
    # ═══════════════════════════════════════════
    
    def get_signal_summary(self) -> str:
        """
        Telegram ke liye readable summary
        """
        if not self.current_signal:
            return "No signal generated yet."
        
        s = self.current_signal
        analysis = self.get_night_analysis()
        
        lines = []
        lines.append("=" * 35)
        
        if s.action in [TradeAction.BUY_CE.value, TradeAction.BUY_PE.value]:
            emoji = "🟢" if s.action == TradeAction.BUY_CE.value else "🔴"
            lines.append(f"{emoji} TRADE SIGNAL: {s.action}")
            lines.append(f"Strike: {s.strike} {s.option_type}")
            lines.append(f"Entry: {s.entry_price_nifty}")
            lines.append(f"SL: {s.sl_nifty}")
            lines.append(f"TP1: {s.tp1_nifty} (50% exit)")
            lines.append(f"TP2: {s.tp2_nifty} (rest exit)")
            lines.append(f"Confidence: {s.confidence}%")
            lines.append(f"EXIT: 10:30 AM PAKKA!")
        elif s.action == TradeAction.SKIP.value:
            lines.append("🟡 SKIP — Setup weak hai")
        else:
            lines.append("⛔ NO TRADE")
        
        lines.append("")
        lines.append("Reasons:")
        for r in s.reasons[-5:]:  # Last 5 reasons
            lines.append(f"  • {r}")
        
        if s.skip_reasons:
            lines.append("")
            lines.append("Skip reasons:")
            for r in s.skip_reasons:
                lines.append(f"  ❌ {r}")
        
        if analysis:
            lines.append("")
            lines.append(f"VIX: {analysis.vix}")
            lines.append(f"Trends: 1D={analysis.trend_1d} 4H={analysis.trend_4h}")
        
        lines.append("=" * 35)
        lines.append("⚠️ Educational only. No guaranteed profit.")
        
        return "\n".join(lines)
