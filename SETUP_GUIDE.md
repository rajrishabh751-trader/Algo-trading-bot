# PURE LIQUIDITY ALGO — SETUP GUIDE
## Rishabh ke liye Step-by-Step Instructions

---

## STEP 1: TELEGRAM BOT BANAO (5 min)

1. **Telegram app kholo** (phone/tab pe)
2. **@BotFather** ko search karo aur message karo
3. `/newbot` type karo
4. Bot ka naam do: `Rishabh Trade Bot` (ya kuch bhi)
5. Username do: `rishabh_trade_123_bot` (unique hona chahiye, _bot se end hona chahiye)
6. BotFather ek **TOKEN** dega — yeh SAVE karo!
   - Example: `7123456789:AAHxyz...`
7. Apne naye bot ko dhundho Telegram mein, message bhejo: `/start`
8. **Chat ID find karo:**
   - Browser mein jao: `https://api.telegram.org/bot<TERA_TOKEN>/getUpdates`
   - JSON mein `"chat":{"id":123456789}` milega
   - Yeh number = tera CHAT ID

---

## STEP 2: CLOUD SERVER SETUP (10 min)

### Option A: Railway.app (RECOMMENDED — Easy!)
1. **https://railway.app** pe jao
2. **GitHub account se signup karo** (ya Google)
3. "New Project" click karo
4. "Deploy from GitHub" select karo
5. Apna algo-system code wahan upload karo
6. Environment variables mein daalo:
   - `TELEGRAM_BOT_TOKEN` = tera bot token
   - `TELEGRAM_CHAT_ID` = tera chat ID
   - `TRADING_MODE` = PAPER
7. Deploy karo — Railway automatically Python detect karega

### Option B: Render.com (FREE tier available!)
1. **https://render.com** pe jao
2. Signup karo (GitHub se)
3. "New Web Service" click karo
4. GitHub se repo connect karo
5. Build Command: `pip install -r requirements.txt`
6. Start Command: `python main.py`
7. Environment variables set karo (same as above)

### Option C: Apna Laptop (Testing ke liye)
1. Python 3.9+ install karo
2. Folder mein jao: `cd algo-system`
3. Run karo: `python main.py --test` (pehle test)
4. Phir: `python main.py` (dashboard start)
5. Browser mein kholo: `http://localhost:8080`

---

## STEP 3: CONFIG FILE EDIT KARO

`config.py` file mein yeh values daalo:

```python
DHAN_CLIENT_ID = "tera_dhan_client_id"
DHAN_ACCESS_TOKEN = "tera_dhan_access_token"
TELEGRAM_BOT_TOKEN = "7123456789:AAHxyz..."
TELEGRAM_CHAT_ID = "123456789"
TRADING_MODE = "PAPER"  # PAPER / SHADOW / LIVE
```

---

## STEP 4: SYSTEM TEST KARO

```bash
python main.py --test
```

Yeh command poora system test karega:
- Night analysis loading ✅
- Pre-trade checks ✅
- First candle analysis (3 scenarios) ✅
- Paper trade simulation ✅
- Exit conditions ✅
- Telegram connection ✅

Sab ✅ dikhe toh system ready hai!

---

## STEP 5: DAILY USE

### RAAT KO (10-11 PM):
1. TradingView pe chart markup karo (Playbook follow karo)
2. Browser mein dashboard kholo: `http://your-server:8080`
3. "Raat Analysis" tab mein saara data daalo
4. "SAVE" karo — Telegram pe confirmation aayegi
5. So jao! 😴

### SUBAH (9:15-9:20 AM):
- **PAPER MODE mein**: Bot khud pehli candle check karega
  (Abhi manual input hai, Dhan API connect karne pe automatic ho jaayega)
- Telegram pe signal aayega: TRADE ya NO TRADE
- Paper trade automatically execute hoga

### 10:30 AM:
- Bot khud exit karega
- Telegram pe P&L aayegi

### SHAAM KO:
- Dashboard pe "Statistics" tab dekho
- Trade review karo

---

## FILE STRUCTURE:

```
algo-system/
├── config.py           ← Settings + API keys
├── strategy_engine.py  ← Pure Liquidity strategy logic
├── telegram_bot.py     ← Telegram notifications
├── paper_trader.py     ← Paper trading simulator
├── dashboard.py        ← Web dashboard
├── main.py             ← Main runner
├── requirements.txt    ← Dependencies
├── SETUP_GUIDE.md      ← Yeh file!
└── data/               ← Trade logs (auto-created)
    ├── trade_log.json
    ├── night_analysis.json
    └── paper_trades.json
```

---

## PHASES:

### Phase 1 (NOW): Paper Trading
- Dashboard + Telegram + Paper trades
- Real data, fake money
- 2-4 weeks tak chalo

### Phase 2 (2-4 weeks baad): Shadow Mode
- Bot signals dega but trade nahi lega
- Tu manually verify karega
- 1-2 weeks

### Phase 3 (1-2 months baad): Live Trading
- Dhan API connect karenge
- 1 lot se start
- Slowly scale up

---

## TROUBLESHOOTING:

**Dashboard nahi khul raha:**
- Check karo port 8080 free hai: `lsof -i :8080`
- `python main.py` run hua?

**Telegram message nahi aa raha:**
- `python main.py --telegram` se test karo
- Token aur Chat ID check karo
- Bot ko /start bheja?

**Night analysis save nahi ho raha:**
- `data/` folder exist karta hai?
- Permission issue? `chmod 777 data/`

---

## IMPORTANT NOTES:

⚠️ PAPER MODE mein start karo — LIVE mat karo abhi!
⚠️ Minimum 20-30 paper trades ke baad hi LIVE consider karo
⚠️ API keys kisi ke saath SHARE mat karo
⚠️ Educational only — profit guaranteed nahi hai
