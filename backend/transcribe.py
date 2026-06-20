"""
Whisper ile ses → metin dönüştürme modülü.
faster-whisper (CTranslate2) kullanarak ~4x daha hızlı çalışır.
"""

import os
import sys
import tempfile

# nvidia-cublas-cu12 / nvidia-cudnn-cu12 pip DLL'lerini işlem belleğine yükle.
# ctypes.CDLL Windows DLL önbelleğine ekler; CTranslate2 sonradan "bulur".
# os.add_dll_directory() tek başına yetersiz kalabilir.
def _preload_nvidia_dlls() -> None:
    import ctypes
    import glob
    import site

    priority = ("cublas64", "cublasLt64", "cudnn")  # Önce yüklenmesi gerekenler

    def _try_load(path: str) -> None:
        try:
            ctypes.CDLL(path)
        except OSError:
            pass

    for sp in site.getsitepackages():
        nvidia_dir = os.path.join(sp, "nvidia")
        if not os.path.isdir(nvidia_dir):
            continue

        all_dlls = glob.glob(os.path.join(nvidia_dir, "**", "*.dll"), recursive=True)

        # Önce kritik DLL'leri yükle
        for name in priority:
            for dll in all_dlls:
                if name.lower() in os.path.basename(dll).lower():
                    _try_load(dll)

        # Sonra kalanları yükle
        for dll in all_dlls:
            _try_load(dll)

        # add_dll_directory de ekle (ikili güvence)
        if hasattr(os, "add_dll_directory"):
            for dll in all_dlls:
                bin_dir = os.path.dirname(dll)
                try:
                    os.add_dll_directory(bin_dir)
                except OSError:
                    pass

        print(f"✅ NVIDIA DLL'leri önceden yüklendi ({len(all_dlls)} dosya)")
        break  # İlk geçerli site-packages yeterli

_preload_nvidia_dlls()

# ffmpeg yolunu PATH'e ekle (ses işlemesi için gerekli)
try:
    import imageio_ffmpeg
    import shutil
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.join(os.path.dirname(ffmpeg_exe), "_ffmpeg_alias")
    os.makedirs(ffmpeg_dir, exist_ok=True)
    ffmpeg_alias = os.path.join(ffmpeg_dir, "ffmpeg.exe")
    if not os.path.exists(ffmpeg_alias):
        shutil.copy2(ffmpeg_exe, ffmpeg_alias)
        print(f"✅ ffmpeg.exe oluşturuldu: {ffmpeg_alias}")
    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
        print(f"✅ ffmpeg PATH'e eklendi: {ffmpeg_dir}")
except ImportError:
    print("⚠️ imageio_ffmpeg bulunamadı, ffmpeg sistem PATH'inde olmalı")

from faster_whisper import WhisperModel

import gc

_CURRENT_MODEL = None
_CURRENT_MODEL_SIZE = None

def _get_or_load_model(model_size: str) -> WhisperModel:
    global _CURRENT_MODEL, _CURRENT_MODEL_SIZE
    
    # İstenen model aynıysa mevcut modeli döndür
    if _CURRENT_MODEL is not None and _CURRENT_MODEL_SIZE == model_size:
        return _CURRENT_MODEL
        
    # Eski modeli bellekten temizle
    if _CURRENT_MODEL is not None:
        print(f"🧹 Eski model temizleniyor ({_CURRENT_MODEL_SIZE})...")
        del _CURRENT_MODEL
        gc.collect()
        _CURRENT_MODEL = None
        _CURRENT_MODEL_SIZE = None

    # Yeni modeli yükle
    try:
        print(f"🔄 Whisper modeli yükleniyor ({model_size}, CUDA/GPU)...")
        m = WhisperModel(model_size, device="cuda", compute_type="float16")
        print(f"✅ Whisper modeli hazır! (CUDA float16 — GPU modunda {model_size} 🚀)")
    except Exception as cuda_err:
        print(f"⚠️ CUDA hatası ({cuda_err}), CPU moduna geçiliyor...")
        m = WhisperModel(model_size, device="cpu", compute_type="int8")
        print(f"✅ Whisper modeli hazır! (int8 — CPU modunda {model_size})")

    _CURRENT_MODEL = m
    _CURRENT_MODEL_SIZE = model_size
    return m


def transcribe_audio(audio_bytes: bytes, model_size: str = "small") -> str:
    """
    WAV formatındaki ses verisini metne çevirir.
    faster-whisper ile ~4x daha hızlı çalışır.
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        tmp_file.write(audio_bytes)
        tmp_path = tmp_file.name

    try:
        model = _get_or_load_model(model_size)
        segments, info = model.transcribe(
            tmp_path,
            language="en",
            beam_size=1,          # Hız için beam_size=1
            best_of=1,            # Hız için tek deneme
            vad_filter=True,      # Sessiz kısımları atla
            vad_parameters=dict(
                min_silence_duration_ms=500,
            ),
        )

        # Segmentleri birleştir
        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())

        text = " ".join(text_parts).strip()
        print(f"📝 Tanınan metin: {text}")
        return text

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
