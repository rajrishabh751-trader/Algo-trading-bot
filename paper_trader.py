"""
╔══════════════════════════════════════════════════╗
║   PAPER TRADING SIMULATOR                        ║
║   Real data, fake money — safest way to test     ║
╚══════════════════════════════════════════════════╝

Yeh module real market data use karega but actual trade nahi lega.
Sab simulated hai — P&L track hoga but paisa nahi lagega.
"""

import json
import os
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import Optional, List
import config
from strategy_engine import (
    StrategyEngine, TradeSignal, TradeRecord, Candle, 
    TradeAction, ExitReason
)
from telegram_bot import TelegramBot


@dataclass
class PaperPosition:
    """Active paper trade position"""
    entry_time: str
    option_type: str          # CE or PE
    strike: float
    entry_nifty: float        # Nifty at entry
    entry_premium: float      # Estimated option premium
    quantity: int              # Number of lots * lot size
    sl_nifty: float
    tp1_nifty: float
    tp2_nifty: float
    tp1_hit: bool = False     # TP1 already hit?
    remaining_qty: int = 0    # After TP1 partial exit
    sl_moved_to_be: bool = False  # SL moved to breakeven?
    pnl: float = 0
    
    def __post_init__(self):
        if self.remaining_qty == 0:
            self.remaining_qty = self.quantity


class PaperTrader:
    """
    Paper Trading Engine
    
    Flow:
    1. Raat ko: Dashboard se night analysis save karo
    2. Subah 9:20: Bot pehli candle data fetch karega
    3. Strategy engine signal generate karega  
    4. Paper trader simulated entry lega
    5. Har minute price check karega
    6. SL/TP/10:30 pe exit karega
    7. P&L calculate karke Telegram pe bhejega
    """
    
    def __init__(self):
        self.engine = StrategyEngine()
        self.telegram = TelegramBot()
        self.active_position: Optional[PaperPosition] = None
        self.today_pnl: float = 0
        self.paper_trades: List[dict] = []
        
        # Load existing paper trades
        self._load_trades()
    
    def _load_trades(self):
        """Load saved paper trades"""
        try:
            if os.path.exists(config.PAPER_TRADES_FILE):
                with open(config.PAPER_TRADES_FILE, 'r') as f:
                    self.paper_trades = json.load(f)
        except (json.JSONDecodeError, Exception):
            self.paper_trades = []
    
    def _save_trades(self):
        """Save paper trades"""
        os.makedirs(config.DATA_DIR, exist_ok=True)
        with open(config.PAPER_TRADES_FILE, 'w') as f:
            json.dump(self.paper_trades, f, indent=2)
    
    # ═══════════════════════════════════════════
    # ESTIMATE OPTION PREMIUM
    # ═══════════════════════════════════════════
    
    def estimate_premium(self, nifty_price: float, strike: float, 
                         option_type: str, vix: float = 14) -> float:
        """
        Simple premium estimation (ATM option)
        
        ATM option ka premium roughly:
        - Delta ~0.5
        - Nifty ke 50 point move pe premium ~25-30 point move
        - VIX ka effect: higher VIX = higher premium
        
        Yeh approximation hai — exact premium Dhan API se milega live mein
        """
        # Base ATM premium estimate
        # ATM options typically trade at ~150-250 for weekly, ~200-400 for monthly
        # Simplified estimation
        time_to_expiry_factor = 1.0  # Monthly expiry = more premium
        vix_factor = vix / 14.0     # Normalize to typical VIX
        
        base_premium = 180 * vix_factor * time_to_expiry_factor
        
        # Intrinsic value adjustment
        if option_type == "CE":
            intrinsic = max(0, nifty_price - strike)
        else:
            intrinsic = max(0, strike - nifty_price)
        
        return round(base_premium + intrinsic, 2)
    
    def estimate_premium_change(self, nifty_move: float, option_type: str) -> float:
        """
        Estimate premium change for a Nifty move
        ATM delta ~0.5, so 50 pt Nifty move = ~25 pt premium move
        """
        delta = 0.5  # ATM approximate delta
        if option_type == "PE":
            delta = -0.5
        
        return round(nifty_move * abs(delta), 2)
    
    # ═══════════════════════════════════════════
    # PROCESS FIRST CANDLE
    # ═══════════════════════════════════════════
    
    def process_first_candle(self, candle_data: dict) -> dict:
        """
        Pehli candle aane pe — full analysis + paper entry
        
        candle_data format:
        {
            "open": 24850,
            "high": 24900, 
            "low": 24810,
            "close": 24880,
            "volume": 50000,
            "timestamp": "2026-03-04 09:20:00"
        }
        
        Returns: Complete result dict
        """
        result = {
            "status": "PROCESSED",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "candle": candle_data,
            "signal": None,
            "position": None,
            "message": ""
        }
        
        # Create Candle object
        candle = Candle(
            timestamp=candle_data.get("timestamp", ""),
            open=candle_data["open"],
            high=candle_data["high"],
            low=candle_data["low"],
            close=candle_data["close"],
            volume=candle_data.get("volume", 0)
        )
        
        # Send Telegram alert about first candle
        self.telegram.send_first_candle_alert({
            **candle_data,
            "body_percent": candle.body_percent
        })
        
        # Analyze with strategy engine
        signal = self.engine.analyze_first_candle(candle)
        result["signal"] = signal.to_dict()
        
        # Send signal to Telegram
        signal_summary = self.engine.get_signal_summary()
        self.telegram.send_trade_signal(signal_summary)
        
        # Take paper trade if signal says so
        if signal.action in [TradeAction.BUY_CE.value, TradeAction.BUY_PE.value]:
            position = self._open_paper_position(signal, candle)
            result["position"] = asdict(position)
            result["message"] = f"Paper {signal.action} entry at {signal.strike} {signal.option_type}"
            
            # Send entry alert
            analysis = self.engine.get_night_analysis()
            vix = analysis.vix if analysis else 14
            premium = self.estimate_premium(
                candle.close, signal.strike, signal.option_type, vix
            )
            
            self.telegram.send_entry_executed({
                "type": f"{signal.option_type} (PAPER)",
                "strike": signal.strike,
                "premium": f"~{premium:.0f}",
                "quantity": f"{config.LOT_SIZE} (1 lot)",
                "sl": signal.sl_nifty,
                "tp1": signal.tp1_nifty,
                "tp2": signal.tp2_nifty
            })
        
        elif signal.action == TradeAction.SKIP.value:
            result["message"] = "SKIP — Setup weak"
            self.telegram.send_no_trade(signal.skip_reasons)
        
        else:
            result["message"] = "NO TRADE"
            self.telegram.send_no_trade(signal.skip_reasons or signal.reasons)
        
        return result
    
    def _open_paper_position(self, signal: TradeSignal, candle: Candle) -> PaperPosition:
        """Open a paper trade position"""
        analysis = self.engine.get_night_analysis()
        vix = analysis.vix if analysis else 14
        
        premium = self.estimate_premium(
            candle.close, signal.strike, signal.option_type, vix
        )
        
        self.active_position = PaperPosition(
            entry_time=datetime.now().strftime("%H:%M:%S"),
            option_type=signal.option_type,
            strike=signal.strike,
            entry_nifty=candle.close,
            entry_premium=premium,
            quantity=config.LOT_SIZE * config.MAX_LOTS,
            sl_nifty=signal.sl_nifty,
            tp1_nifty=signal.tp1_nifty,
            tp2_nifty=signal.tp2_nifty,
        )
        
        return self.active_position
    
    # ═══════════════════════════════════════════
    # PRICE UPDATE — Har minute call karo
    # ═══════════════════════════════════════════
    
    def update_price(self, current_nifty: float, current_time: str) -> Optional[dict]:
        """
        Har minute ya tick pe call karo with current Nifty price
        
        Returns: Exit action dict if exit needed, None if hold
        """
        if not self.active_position:
            return None
        
        pos = self.active_position
        
        # Check exit conditions
        exit_check = self.engine.check_exit_conditions(current_nifty, current_time)
        
        if not exit_check:
            return None  # Hold position
        
        action = exit_check["action"]
        
        if action == "PARTIAL_EXIT" and not pos.tp1_hit:
            # TP1 hit — 50% exit
            return self._handle_tp1(current_nifty, exit_check)
        
        elif action in ["EXIT_ALL", "PARTIAL_EXIT"]:
            # Full exit (SL/TP2/Time/TP1 already hit so this is remaining)
            return self._handle_full_exit(current_nifty, current_time, exit_check)
        
        return None
    
    def _handle_tp1(self, current_nifty: float, exit_data: dict) -> dict:
        """TP1 hit — partial exit"""
        pos = self.active_position
        pos.tp1_hit = True
        
        # Calculate partial P&L
        nifty_move = current_nifty - pos.entry_nifty
        if pos.option_type == "PE":
            nifty_move = -nifty_move  # For PE, down move is profit
        
        premium_change = self.estimate_premium_change(nifty_move, pos.option_type)
        partial_qty = int(pos.quantity * config.TP1_EXIT_PERCENT / 100)
        partial_pnl = premium_change * partial_qty
        
        pos.remaining_qty = pos.quantity - partial_qty
        pos.pnl += partial_pnl
        
        # Move SL to breakeven
        pos.sl_nifty = pos.entry_nifty
        pos.sl_moved_to_be = True
        
        # Telegram alert
        self.telegram.send_tp1_hit({
            "nifty": current_nifty,
            "new_sl": pos.entry_nifty,
            "partial_pnl": f"Rs. {partial_pnl:+,.0f}"
        })
        
        return {
            "action": "PARTIAL_EXIT",
            "tp1_pnl": partial_pnl,
            "remaining_qty": pos.remaining_qty,
            "new_sl": pos.entry_nifty,
            "message": f"TP1 HIT! 50% exit. P&L: Rs. {partial_pnl:+,.0f}. SL → breakeven."
        }
    
    def _handle_full_exit(self, current_nifty: float, current_time: str, 
                          exit_data: dict) -> dict:
        """Full exit — close everything"""
        pos = self.active_position
        
        # Calculate remaining P&L
        nifty_move = current_nifty - pos.entry_nifty
        if pos.option_type == "PE":
            nifty_move = -nifty_move
        
        premium_change = self.estimate_premium_change(nifty_move, pos.option_type)
        remaining_pnl = premium_change * pos.remaining_qty
        total_pnl = pos.pnl + remaining_pnl
        
        # Create trade record
        trade_record = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "type": f"{pos.option_type} (PAPER)",
            "strike": pos.strike,
            "entry_nifty": pos.entry_nifty,
            "exit_nifty": current_nifty,
            "entry_premium": pos.entry_premium,
            "nifty_move": nifty_move if pos.option_type == "CE" else -nifty_move,
            "quantity": pos.quantity,
            "tp1_hit": pos.tp1_hit,
            "exit_reason": exit_data.get("exit_type", "UNKNOWN"),
            "exit_time": current_time,
            "pnl": round(total_pnl, 2),
            "mode": "PAPER"
        }
        
        # Save trade
        self.paper_trades.append(trade_record)
        self._save_trades()
        
        # Log in engine
        self.engine.log_trade(TradeRecord(
            date=trade_record["date"],
            signal=self.engine.current_signal.to_dict() if self.engine.current_signal else {},
            entry_time=pos.entry_time,
            exit_time=current_time,
            entry_price=pos.entry_premium,
            pnl=round(total_pnl, 2),
            exit_reason=exit_data.get("exit_type", "")
        ))
        
        # Telegram alert
        self.telegram.send_exit_alert({
            "reason": exit_data.get("reason", ""),
            "entry_price": f"{pos.entry_nifty} (Nifty)",
            "exit_price": f"{current_nifty} (Nifty)",
            "pnl": round(total_pnl, 2)
        })
        
        # Reset
        self.today_pnl += total_pnl
        self.active_position = None
        
        return {
            "action": "FULL_EXIT",
            "pnl": round(total_pnl, 2),
            "exit_reason": exit_data.get("reason", ""),
            "trade_record": trade_record,
            "message": f"TRADE CLOSED! P&L: Rs. {total_pnl:+,.0f}"
        }
    
    # ═══════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════
    
    def get_stats(self) -> dict:
        """Overall paper trading statistics"""
        if not self.paper_trades:
            return {
                "total_trades": 0,
                "message": "Abhi tak koi paper trade nahi hua."
            }
        
        total = len(self.paper_trades)
        wins = sum(1 for t in self.paper_trades if t.get("pnl", 0) > 0)
        losses = sum(1 for t in self.paper_trades if t.get("pnl", 0) < 0)
        breakeven = total - wins - losses
        
        total_pnl = sum(t.get("pnl", 0) for t in self.paper_trades)
        avg_win = 0
        avg_loss = 0
        
        winning_trades = [t["pnl"] for t in self.paper_trades if t.get("pnl", 0) > 0]
        losing_trades = [t["pnl"] for t in self.paper_trades if t.get("pnl", 0) < 0]
        
        if winning_trades:
            avg_win = sum(winning_trades) / len(winning_trades)
        if losing_trades:
            avg_loss = sum(losing_trades) / len(losing_trades)
        
        win_rate = (wins / total * 100) if total > 0 else 0
        
        # Streak
        current_streak = 0
        streak_type = ""
        for t in reversed(self.paper_trades):
            pnl = t.get("pnl", 0)
            if not streak_type:
                streak_type = "WIN" if pnl > 0 else "LOSS"
            
            if (streak_type == "WIN" and pnl > 0) or (streak_type == "LOSS" and pnl < 0):
                current_streak += 1
            else:
                break
        
        return {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "breakeven": breakeven,
            "win_rate": round(win_rate, 1),
            "total_pnl": round(total_pnl, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "current_streak": f"{current_streak} {streak_type}" if streak_type else "N/A",
            "last_5_trades": self.paper_trades[-5:] if len(self.paper_trades) >= 5 else self.paper_trades,
            "today_pnl": round(self.today_pnl, 2)
        }
    
    def reset_daily(self):
        """New day reset"""
        self.active_position = None
        self.today_pnl = 0
        self.engine.reset_daily()
