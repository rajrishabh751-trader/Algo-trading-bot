"""
╔══════════════════════════════════════════════════╗
║   TELEGRAM BOT — Trade Notifications             ║
║   Tujhe phone pe alerts milenge                  ║
╚══════════════════════════════════════════════════╝

Setup:
1. Telegram pe @BotFather ko message karo
2. /newbot command do
3. Bot name do: "RishabhTradeBot" (ya kuch bhi)
4. Username do: "rishabh_trade_bot" (unique hona chahiye)
5. BotFather token dega — config.py mein daalo
6. Apne bot ko message karo, phir /start bhejo
7. Chat ID ke liye: https://api.telegram.org/bot<TOKEN>/getUpdates
"""

import json
import asyncio
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError
from urllib.parse import quote
import config


class TelegramBot:
    """Simple Telegram bot for sending trade alerts"""
    
    def __init__(self):
        self.token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.enabled = self.token != "YOUR_BOT_TOKEN_HERE"
    
    def send_message(self, text: str, parse_mode: str = None) -> bool:
        """
        Telegram pe message bhejo
        Returns: True if sent, False if failed
        """
        if not self.enabled:
            print(f"[TELEGRAM DISABLED] {text}")
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": text,
            }
            if parse_mode:
                data["parse_mode"] = parse_mode
            
            payload = json.dumps(data).encode('utf-8')
            req = Request(url, data=payload, headers={
                'Content-Type': 'application/json'
            })
            
            response = urlopen(req, timeout=10)
            result = json.loads(response.read().decode())
            return result.get("ok", False)
        
        except URLError as e:
            print(f"[TELEGRAM ERROR] {e}")
            return False
        except Exception as e:
            print(f"[TELEGRAM ERROR] {e}")
            return False
    
    # ═══════════════════════════════════════════
    # PRE-BUILT MESSAGE TEMPLATES
    # ═══════════════════════════════════════════
    
    def send_morning_start(self):
        """Subah market open hone se pehle"""
        now = datetime.now().strftime("%d-%b-%Y %H:%M")
        msg = (
            f"🌅 GOOD MORNING — {now}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Market 9:15 AM pe khulega.\n"
            f"Pehli 5M candle ka wait karo...\n"
            f"Mode: {config.TRADING_MODE}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        return self.send_message(msg)
    
    def send_first_candle_alert(self, candle_data: dict):
        """Pehli candle complete hone pe"""
        direction = "🟢 GREEN" if candle_data.get('close', 0) > candle_data.get('open', 0) else "🔴 RED"
        body_pct = candle_data.get('body_percent', 0)
        
        msg = (
            f"📊 PEHLI CANDLE COMPLETE (9:15-9:20)\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Direction: {direction}\n"
            f"Open:  {candle_data.get('open', 'N/A')}\n"
            f"High:  {candle_data.get('high', 'N/A')}\n"
            f"Low:   {candle_data.get('low', 'N/A')}\n"
            f"Close: {candle_data.get('close', 'N/A')}\n"
            f"Body:  {body_pct:.1f}%\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Analyzing..."
        )
        return self.send_message(msg)
    
    def send_trade_signal(self, signal_text: str):
        """Trade signal bhejo"""
        return self.send_message(signal_text)
    
    def send_entry_executed(self, entry_data: dict):
        """Entry execute hone pe"""
        msg = (
            f"✅ ENTRY EXECUTED!\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Type: {entry_data.get('type', 'N/A')}\n"
            f"Strike: {entry_data.get('strike', 'N/A')}\n"
            f"Premium: {entry_data.get('premium', 'N/A')}\n"
            f"Qty: {entry_data.get('quantity', 'N/A')}\n"
            f"SL: {entry_data.get('sl', 'N/A')}\n"
            f"TP1: {entry_data.get('tp1', 'N/A')}\n"
            f"TP2: {entry_data.get('tp2', 'N/A')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⏰ EXIT at 10:30 AM — NO EXCEPTION!"
        )
        return self.send_message(msg)
    
    def send_exit_alert(self, exit_data: dict):
        """Exit hone pe"""
        pnl = exit_data.get('pnl', 0)
        emoji = "💰" if pnl > 0 else "📉" if pnl < 0 else "➖"
        
        msg = (
            f"{emoji} TRADE CLOSED\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Reason: {exit_data.get('reason', 'N/A')}\n"
            f"Entry: {exit_data.get('entry_price', 'N/A')}\n"
            f"Exit:  {exit_data.get('exit_price', 'N/A')}\n"
            f"P&L:   Rs. {pnl:+,.0f}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{'Well done! System follow kiya! 💪' if pnl >= 0 else 'Loss = part of system. Kal naya din! 🙏'}"
        )
        return self.send_message(msg)
    
    def send_tp1_hit(self, data: dict):
        """TP1 hit pe"""
        msg = (
            f"🎯 TP1 HIT! — 50% EXIT\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Nifty: {data.get('nifty', 'N/A')}\n"
            f"50% quantity exit kiya.\n"
            f"SL moved to breakeven: {data.get('new_sl', 'N/A')}\n"
            f"Remaining target: TP2 ya 10:30 exit\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        return self.send_message(msg)
    
    def send_no_trade(self, reasons: list):
        """No trade decision pe"""
        reason_text = "\n".join([f"  ❌ {r}" for r in reasons[:5]])
        msg = (
            f"⛔ NO TRADE TODAY\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{reason_text}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Patience = Superpower! 🧘"
        )
        return self.send_message(msg)
    
    def send_night_analysis_saved(self, analysis_data: dict):
        """Raat ka analysis save hone pe"""
        msg = (
            f"🌙 RAAT KA ANALYSIS SAVED\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"1D Trend: {analysis_data.get('trend_1d', 'N/A')}\n"
            f"4H Trend: {analysis_data.get('trend_4h', 'N/A')}\n"
            f"1H Bias:  {analysis_data.get('bias_1h', 'N/A')}\n"
            f"VIX:      {analysis_data.get('vix', 'N/A')}\n"
            f"BSL Swept: {'YES' if analysis_data.get('bsl_swept') else 'NO'}\n"
            f"SSL Swept: {'YES' if analysis_data.get('ssl_swept') else 'NO'}\n"
            f"Confidence: {analysis_data.get('confidence', 'N/A')}%\n"
            f"Direction: {analysis_data.get('preferred_direction', 'NONE')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Subah 9:15 pe bot khud check karega. So jao! 😴"
        )
        return self.send_message(msg)
    
    def send_daily_summary(self, summary: dict):
        """Shaam ka summary"""
        total_trades = summary.get('total_trades', 0)
        total_pnl = summary.get('total_pnl', 0)
        
        msg = (
            f"📋 DAILY SUMMARY\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Date: {summary.get('date', 'N/A')}\n"
            f"Trades: {total_trades}\n"
            f"P&L: Rs. {total_pnl:+,.0f}\n"
            f"Mode: {config.TRADING_MODE}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Raat ko analysis karna mat bhoolna! 🌙"
        )
        return self.send_message(msg)
    
    def send_error(self, error_msg: str):
        """Error hone pe"""
        msg = (
            f"⚠️ SYSTEM ERROR\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{error_msg}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Check karo! Trade manually if needed."
        )
        return self.send_message(msg)
    
    # ═══════════════════════════════════════════
    # UTILITY
    # ═══════════════════════════════════════════
    
    def get_chat_id(self) -> str:
        """Get chat ID from recent messages (setup helper)"""
        if not self.enabled:
            return "Bot token not set"
        
        try:
            url = f"{self.base_url}/getUpdates"
            req = Request(url)
            response = urlopen(req, timeout=10)
            result = json.loads(response.read().decode())
            
            if result.get("ok") and result.get("result"):
                for update in result["result"]:
                    chat = update.get("message", {}).get("chat", {})
                    if chat:
                        return str(chat.get("id", "Not found"))
            return "No messages found. Bot ko pehle /start bhejo!"
        
        except Exception as e:
            return f"Error: {e}"
    
    def test_connection(self) -> bool:
        """Test if bot is working"""
        return self.send_message("🤖 Bot connected! Trading system ready.")
