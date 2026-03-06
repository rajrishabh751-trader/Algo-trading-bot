"""
╔══════════════════════════════════════════════════╗
║   PURE LIQUIDITY ALGO — MAIN RUNNER              ║
║   Yeh file run karo aur system start ho jaayega  ║
╚══════════════════════════════════════════════════╝

Usage:
  python main.py              → Dashboard start (default)
  python main.py --test       → Test mode with sample data
  python main.py --telegram   → Test Telegram connection
  python main.py --stats      → Show paper trade stats
"""

import sys
import os
import json
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from strategy_engine import StrategyEngine, Candle, NightAnalysis
from paper_trader import PaperTrader
from telegram_bot import TelegramBot
from dashboard import start_dashboard


def test_system():
    """
    Full system test with sample data
    Yeh run karo pehle — dekho sab kaam kar raha hai
    """
    print("\n" + "=" * 50)
    print("  PURE LIQUIDITY SYSTEM — TEST MODE")
    print("=" * 50)
    
    engine = StrategyEngine()
    paper = PaperTrader()
    telegram = TelegramBot()
    
    # Step 1: Load sample night analysis
    print("\n[1] Loading sample night analysis...")
    sample_analysis = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "trend_1d": "BEARISH",
        "trend_4h": "BEARISH",
        "bias_1h": "NEUTRAL",
        "major_ssl": 25800,
        "minor_ssl": 25400,
        "eq_zone": 25100,
        "minor_bsl": 24800,
        "major_bsl": 24600,
        "bsl_swept": True,
        "ssl_swept": False,
        "max_ce_oi_strike": 25500,
        "max_pe_oi_strike": 24500,
        "vix": 14.5,
        "ob_zone_high": 24750,
        "ob_zone_low": 24700,
        "red_news_event": False,
        "news_note": "",
        "preferred_direction": "NONE",
        "confidence": 65,
        "bullish_condition": "Green candle + BSL sweep bounce",
        "bearish_condition": "Red candle + higher TF bearish",
    }
    
    engine.load_night_analysis(sample_analysis)
    print("  ✅ Night analysis loaded")
    print(f"  Trends: 1D={sample_analysis['trend_1d']} 4H={sample_analysis['trend_4h']}")
    print(f"  BSL Swept: {sample_analysis['bsl_swept']}")
    print(f"  VIX: {sample_analysis['vix']}")
    
    # Step 2: Pre-trade checks
    print("\n[2] Running pre-trade checks...")
    can_trade, reasons = engine.pre_trade_checks()
    for r in reasons:
        print(f"  {'✅' if 'PASSED' in r else '⚠️'} {r}")
    
    # Step 3: Test Scenario A — Strong GREEN candle (BSL swept + green = CE expected)
    print("\n[3] Testing Scenario A: Strong GREEN first candle...")
    candle_a = Candle(
        timestamp="2026-03-04 09:20:00",
        open=24850, high=24920, low=24830, close=24910, volume=85000
    )
    print(f"  Candle: O={candle_a.open} H={candle_a.high} L={candle_a.low} C={candle_a.close}")
    print(f"  Body: {candle_a.body_percent:.1f}% | {'GREEN' if candle_a.is_green else 'RED'}")
    
    signal_a = engine.analyze_first_candle(candle_a)
    print(f"\n  SIGNAL: {signal_a.action}")
    if signal_a.strike:
        print(f"  Strike: {signal_a.strike} {signal_a.option_type}")
        print(f"  SL: {signal_a.sl_nifty}")
        print(f"  TP1: {signal_a.tp1_nifty}")
        print(f"  TP2: {signal_a.tp2_nifty}")
    print(f"  Confidence: {signal_a.confidence}%")
    for r in signal_a.reasons:
        print(f"  → {r}")
    for r in signal_a.skip_reasons:
        print(f"  ❌ {r}")
    
    # Reset for next test
    engine.reset_daily()
    engine.load_night_analysis(sample_analysis)
    
    # Step 4: Test Scenario B — Weak candle (should SKIP)
    print("\n[4] Testing Scenario B: Weak/Doji candle...")
    candle_b = Candle(
        timestamp="2026-03-04 09:20:00",
        open=24860, high=24900, low=24820, close=24870, volume=30000
    )
    print(f"  Candle: O={candle_b.open} H={candle_b.high} L={candle_b.low} C={candle_b.close}")
    print(f"  Body: {candle_b.body_percent:.1f}%")
    
    signal_b = engine.analyze_first_candle(candle_b)
    print(f"  SIGNAL: {signal_b.action}")
    for r in signal_b.skip_reasons:
        print(f"  ❌ {r}")
    
    # Reset for next test
    engine.reset_daily()
    
    # Step 5: Test with higher TF conflict
    print("\n[5] Testing Scenario C: Higher TF conflict (1D bearish + green candle)...")
    conflict_analysis = {**sample_analysis, "bsl_swept": False}
    engine.load_night_analysis(conflict_analysis)
    
    candle_c = Candle(
        timestamp="2026-03-04 09:20:00",
        open=24850, high=24930, low=24840, close=24920, volume=70000
    )
    signal_c = engine.analyze_first_candle(candle_c)
    print(f"  Green candle but 1D+4H bearish")
    print(f"  SIGNAL: {signal_c.action}")
    for r in signal_c.skip_reasons:
        print(f"  ❌ {r}")
    
    # Step 6: Paper trade simulation
    print("\n[6] Paper trade full simulation...")
    paper.reset_daily()
    paper.engine.load_night_analysis(sample_analysis)
    
    result = paper.process_first_candle({
        "open": 24850, "high": 24920, "low": 24830, 
        "close": 24910, "volume": 85000,
        "timestamp": "2026-03-04 09:20:00"
    })
    print(f"  Result: {result['message']}")
    
    if paper.active_position:
        # Simulate TP1 hit
        print("\n  Simulating TP1 hit...")
        tp1_result = paper.update_price(24910 + 55, "09:45")
        if tp1_result:
            print(f"  {tp1_result['message']}")
        
        # Simulate 10:30 exit
        print("  Simulating 10:30 exit...")
        exit_result = paper.update_price(24910 + 75, "10:30")
        if exit_result:
            print(f"  {exit_result['message']}")
    
    # Step 7: Stats
    print("\n[7] Paper trading stats:")
    stats = paper.get_stats()
    for k, v in stats.items():
        if k != 'last_5_trades':
            print(f"  {k}: {v}")
    
    # Step 8: Telegram test
    print("\n[8] Telegram connection:")
    if telegram.enabled:
        print("  Telegram bot configured — sending test message...")
        if telegram.test_connection():
            print("  ✅ Telegram working!")
        else:
            print("  ❌ Telegram failed — check token/chat ID")
    else:
        print("  ⚠️ Telegram not configured (token not set)")
        print("  Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in config.py")
    
    print("\n" + "=" * 50)
    print("  TEST COMPLETE!")
    print("  Ab 'python main.py' run karo dashboard ke liye")
    print("=" * 50 + "\n")


def test_telegram():
    """Test Telegram connection"""
    telegram = TelegramBot()
    print("\nTesting Telegram Bot...")
    
    if not telegram.enabled:
        print("❌ Bot token not set!")
        print("Steps:")
        print("1. Telegram pe @BotFather ko message karo")
        print("2. /newbot command do")
        print("3. Token ko config.py mein TELEGRAM_BOT_TOKEN mein daalo")
        print("4. Apne bot ko /start bhejo")
        print("5. Chat ID find karo: python main.py --chatid")
        return
    
    print(f"Token: {telegram.token[:10]}...")
    print(f"Chat ID: {telegram.chat_id}")
    
    if telegram.test_connection():
        print("✅ Bot is working! Check Telegram for message.")
    else:
        print("❌ Failed. Check token and chat ID.")


def get_chat_id():
    """Helper to find chat ID"""
    telegram = TelegramBot()
    if not telegram.enabled:
        print("Set TELEGRAM_BOT_TOKEN first!")
        return
    
    chat_id = telegram.get_chat_id()
    print(f"\nYour Chat ID: {chat_id}")
    print("Isko config.py mein TELEGRAM_CHAT_ID mein daalo")


def show_stats():
    """Show paper trading stats"""
    paper = PaperTrader()
    stats = paper.get_stats()
    
    print("\n" + "=" * 40)
    print("  PAPER TRADING STATISTICS")
    print("=" * 40)
    
    for k, v in stats.items():
        if k == 'last_5_trades':
            print(f"\n  Last 5 trades:")
            for t in v:
                pnl = t.get('pnl', 0)
                emoji = '✅' if pnl > 0 else '❌' if pnl < 0 else '➖'
                print(f"    {emoji} {t.get('date')} | {t.get('type')} | Rs.{pnl:+,.0f} | {t.get('exit_reason')}")
        else:
            print(f"  {k}: {v}")
    
    print("=" * 40 + "\n")


def main():
    """Main entry point"""
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    
    if '--test' in args:
        test_system()
    elif '--telegram' in args:
        test_telegram()
    elif '--chatid' in args:
        get_chat_id()
    elif '--stats' in args:
        show_stats()
    elif '--help' in args or '-h' in args:
        print("""
Pure Liquidity Trading System

Commands:
  python main.py              Start dashboard (default)
  python main.py --test       Run full system test
  python main.py --telegram   Test Telegram bot
  python main.py --chatid     Find your Telegram chat ID
  python main.py --stats      Show paper trade statistics
  python main.py --help       Show this help
        """)
    else:
        # Default: Start dashboard
        start_dashboard()


if __name__ == "__main__":
    main()
