import time
import requests
from concurrent.futures import ThreadPoolExecutor

TELEGRAM_BOT_TOKEN = "8348359031:AAG0SVHf1t8qBxxXVX0WCmBzGgLgfhP89ds"
TELEGRAM_CHAT_ID = "882393304"

invalid_symbols = set()
notified_symbols = {}


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload)
        if r.status_code != 200:
            print("Telegram hatası:", r.text)
    except Exception as e:
        print("Telegram gönderim hatası:", e)


def get_symbols_futures():
    """Binance Futures USDT perpetual sembollerini alır."""
    url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    try:
        data = requests.get(url).json()
        symbols = [
            s["symbol"]
            for s in data["symbols"]
            if s["quoteAsset"] == "USDT"
            and s["contractType"] == "PERPETUAL"
            and s["status"] == "TRADING"
        ]
        return symbols
    except Exception as e:
        print("Sembol alma hatası:", e)
        return []


def get_klines(symbol, interval="1m", limit=2):
    """Sadece son iki mumu alır (en son değişimi görmek için)."""
    if symbol in invalid_symbols:
        return []
    url = "https://fapi.binance.com/fapi/v1/klines"
    try:
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        invalid_symbols.add(symbol)
        return []


def get_funding_rate(symbol):
    """Funding rate bilgisini alır."""
    try:
        url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit=1"
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            if data:
                rate = float(data[0]["fundingRate"]) * 100
                return f"{rate:+.4f}%"
        return "N/A"
    except Exception:
        return "N/A"


def star_rating(boost):
    """Yüzdelik değişime göre yıldız verir."""
    abs_boost = abs(boost)
    if abs_boost >= 3:
        return "⭐️⭐️⭐️"
    elif abs_boost >= 2:
        return "⭐️⭐️"
    elif abs_boost >= 1:
        return "⭐️"
    return ""


def repeat_icon_text(symbol):
    """Her coin için yalnızca tekrar sayısını yazar."""
    if symbol not in notified_symbols:
        notified_symbols[symbol] = 1
        return "✅ İlk kez bulundu"
    else:
        notified_symbols[symbol] += 1
        return f"{notified_symbols[symbol]} kez tekrarlandı"


def process_symbol(symbol):
    if symbol in invalid_symbols:
        return

    data = get_klines(symbol, "1m", limit=2)
    if not data or len(data) < 2:
        return

    try:
        previous_price = float(data[-2][4])
        current_price = float(data[-1][4])

        if previous_price == 0:
            return

        boost = ((current_price - previous_price) / previous_price) * 100
        stars = star_rating(boost)
        if not stars:
            return  # %1 altı değişimleri gösterme

        color = "🟢" if boost > 0 else "🔴"
        repeat_text = repeat_icon_text(symbol)
        funding = get_funding_rate(symbol)

        message = (
            f"💰 #{symbol}\n"
            f"Change: {color}%{boost:+.2f} {stars}\n"
            f"Last Price: {current_price:.6f}\n"
            f"Previous Price: {previous_price:.6f}\n"
            f"Funding Rate: {funding}\n\n"
            f"{repeat_text}"
        )

        send_telegram(message)

    except Exception as e:
        print(f"{symbol} işlem hatası:", e)
        invalid_symbols.add(symbol)


def monitor_boost_panel():
    symbols = get_symbols_futures()
    print(f"{len(symbols)} sembol yüklendi.")

    while True:
        with ThreadPoolExecutor(max_workers=10) as executor:
            for symbol in symbols:
                executor.submit(process_symbol, symbol)
        time.sleep(3)


if __name__ == "__main__":
    monitor_boost_panel()
