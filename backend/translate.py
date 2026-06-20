"""
Çeviri modülü — İngilizce metni Türkçeye çevirir.
Hızlı versiyon: googletrans kullanılır (daha hızlı API).
Fallback: deep-translator.
"""

import requests
import urllib.parse

# LibreTranslate varsayılan adresi
LIBRETRANSLATE_URL = "http://localhost:5000/translate"


def translate_with_libretranslate(text: str, target: str = "tr") -> str | None:
    """LibreTranslate ile çeviri (lokal sunucu)."""
    try:
        response = requests.post(
            LIBRETRANSLATE_URL,
            json={"q": text, "source": "en", "target": target, "format": "text"},
            timeout=5
        )
        if response.status_code == 200:
            return response.json()["translatedText"]
    except (requests.ConnectionError, requests.Timeout):
        pass
    return None


def translate_with_google_fast(text: str, target: str = "tr") -> str | None:
    """Google Translate — hızlı ücretsiz API (resmi olmayan)."""
    try:
        encoded = urllib.parse.quote(text)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl={target}&dt=t&q={encoded}"
        response = requests.get(url, timeout=8, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        if response.status_code == 200:
            data = response.json()
            translated = "".join(part[0] for part in data[0] if part[0])
            return translated
    except Exception:
        pass
    return None


def translate_with_deep_translator(text: str, target: str = "tr") -> str:
    """deep-translator kütüphanesi ile Google Translate (yavaş fallback)."""
    from deep_translator import GoogleTranslator
    translator = GoogleTranslator(source="en", target=target)
    return translator.translate(text)


def translate_text(text: str, target: str = "tr") -> str:
    """
    Metni çevirir. Öncelik sırası:
    1. LibreTranslate (lokal)
    2. Google Translate hızlı API
    3. deep-translator (fallback)
    """
    if not text or not text.strip():
        return ""

    # 1. LibreTranslate
    result = translate_with_libretranslate(text, target)
    if result:
        print(f"🌐 LibreTranslate: {result}")
        return result

    # 2. Google Translate hızlı
    result = translate_with_google_fast(text, target)
    if result:
        print(f"🌐 Google (hızlı): {result}")
        return result

    # 3. Fallback
    result = translate_with_deep_translator(text, target)
    print(f"🌐 deep-translator: {result}")
    return result
