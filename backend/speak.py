"""
Supertonic Yerel TTS (on-device) — metin → ses.
Cihaz üzerinde internet gerektirmeden çalışan yüksek kaliteli çok dilli seslendirme motoru.
"""

import io
import re
import base64
import soundfile as sf
from supertonic import TTS

VOICE_MALE = "M1"
VOICE_FEMALE = "F1"
DEFAULT_VOICE = VOICE_MALE
DEFAULT_RATE = "+0%"

_tts_instance = None

def get_tts() -> TTS:
    """Yerel Supertonic modelini tekil (Singleton) olarak yükler ve döndürür."""
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = TTS(auto_download=True)
    return _tts_instance


def preload_model() -> None:
    """Sunucu başlangıcında modeli önceden yükleyerek ilk dublaj işleminde gecikmeyi önler."""
    try:
        print("⏳ Supertonic modeli önbelleğe yükleniyor (cihaz üzerinde çalışmaya hazır)...")
        get_tts()
        print("✅ Supertonic modeli başarıyla yüklendi.")
    except Exception as e:
        print(f"⚠️ Supertonic ön yükleme hatası: {str(e)}")


def parse_rate_to_speed(rate_str: str) -> float:
    """
    Arayüzden gelen yüzde formatındaki hızı (+20%, -10% vb.)
    Supertonic'in beklediği float (0.7 - 2.0) formatına dönüştürür.
    """
    if not rate_str:
        return 1.0
    try:
        rate_str = rate_str.strip()
        if rate_str.endswith("%"):
            val = float(rate_str.replace("%", ""))
            speed = 1.0 + (val / 100.0)
            return max(0.7, min(2.0, speed))
    except Exception:
        pass
    return 1.0


def inject_auto_expressions(text: str) -> str:
    """
    Metin içerisine konuşma akışını doğallaştıracak nefes, gülüş veya iç çekiş
    gibi Supertonic ifade etiketlerini enjekte eder.
    """
    if not text or not text.strip():
        return text

    # Gülüş ifadeleri için <laugh> etiketi ekleme
    laughter_words = [
        "haha", "hehe", "kıkır", "komik", "gülünç", "funny", "laugh", "lol", 
        "gülmek", "güldüm", "şaka", "joke", "komedi"
    ]
    for w in laughter_words:
        if re.search(rf"\b{w}\b", text, re.IGNORECASE):
            text = text.rstrip(".!? ") + " <laugh>."
            break

    # İç çekiş / bekleme durumları için <sigh> etiketi ekleme
    sigh_words = ["ah", "of", "off", "hey", "yazık", "sad", "sigh", "eyvah", "eyvallah"]
    for w in sigh_words:
        if re.search(rf"\b{w}\b", text, re.IGNORECASE):
            text = "<sigh> " + text
            break

    # Cümle sonlarına doğal nefes <breath> etiketi ekleme
    # "Merhaba dünya. Nasılsın?" -> "Merhaba dünya. <breath> Nasılsın?"
    text = re.sub(r"([.!?])\s+", r"\1 <breath> ", text)
    
    return text


async def generate_speech_async(
    text: str,
    voice: str = DEFAULT_VOICE,
    rate: str = DEFAULT_RATE,
    lang: str = "tr",
    auto_expressions: bool = False
) -> bytes:
    """Supertonic ile metni yerel olarak sese çevirir ve WAV baytlarını döndürür."""
    try:
        tts = get_tts()
        
        # Otomatik ifade enjeksiyonu aktifse metni filtrele
        if auto_expressions:
            text = inject_auto_expressions(text)
            print(f"🎭 İfade etiketli metin: {text}")

        # Ses stilini al (M1-M5, F1-F5)
        voice_clean = voice.strip()
        if voice_clean not in ["M1", "M2", "M3", "M4", "M5", "F1", "F2", "F3", "F4", "F5"]:
            voice_style_name = VOICE_MALE
        else:
            voice_style_name = voice_clean

        style = tts.get_voice_style(voice_name=voice_style_name)
        speed = parse_rate_to_speed(rate)

        # Sentezleme
        wav, duration = tts.synthesize(
            text=text,
            lang=lang,
            voice_style=style,
            total_steps=8,
            speed=speed
        )

        # NumPy array'i hafızada WAV formatına çevir
        buffer = io.BytesIO()
        sf.write(buffer, wav.squeeze(), 44100, format='WAV')
        audio_bytes = buffer.getvalue()
        return audio_bytes

    except Exception as e:
        print(f"⚠️ Supertonic TTS Hatası: {str(e)}")
        return b""


async def text_to_speech(
    text: str,
    voice: str = DEFAULT_VOICE,
    rate: str = DEFAULT_RATE,
    lang: str = "tr",
    auto_expressions: bool = False
) -> str:
    """Metni sese çevirip base64 formatında döndürür."""
    if not text or not text.strip():
        return ""

    audio_bytes = await generate_speech_async(text, voice, rate, lang, auto_expressions)
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    print(f"🔊 Ses oluşturuldu (Supertonic): {len(audio_bytes)} bytes (dil: {lang}, hız: {rate})")

    return audio_base64
