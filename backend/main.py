"""
YouTube Anlık Türkçe Çeviri — FastAPI Backend Sunucusu (Hızlı Versiyon)

Optimizasyonlar:
  - faster-whisper (CTranslate2, int8 quantized) — ~4x daha hızlı
  - Edge TTS hÄ±z ayarı (+0% varsayılan)
  - VAD filtresi ile sessiz kÄ±sÄ±mlar atlanıyor
"""

from __future__ import annotations

import asyncio
import base64
import os
import shutil
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.routing import APIRoute
from starlette.background import BackgroundTask

from jobs_store import JOBS, JobState, prune_old_jobs
from speak import text_to_speech, preload_model
from transcribe import transcribe_audio
from translate import translate_text
from video_pipeline import dub_video, download_youtube


@asynccontextmanager
async def _lifespan(app: FastAPI):
    preload_model()
    lines = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            methods = ",".join(sorted(route.methods))
            lines.append(f"  [{methods:18}] {route.path}")
    lines.sort()
    print("\n" + "=" * 62)
    print("YouTube TR API — HTTP rotalari (POST /api/dub/start-url ve /api/jobs olmali)")
    print("=" * 62)
    for ln in lines:
        print(ln)
    print("=" * 62)
    print("Istek loglari asagida (404 gorurseniz yolu kontrol edin).\n")
    yield
    print("\n[shutdown] Sunucu kapatildi.\n")


app = FastAPI(
    title="YouTube TR Çeviri API",
    description="YouTube videolarÄ±nÄ± anlÄ±k olarak Türkçeye Ã§evirir (Hızlı Mod)",
    version="2.0.0",
    lifespan=_lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = Path(__file__).resolve().parent.parent / "frontend"
# 1x1 seffaf PNG — tarayici /favicon.ico ister; 404 access log kirini onler
_FAVICON_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+X2ZkAAAAASUVORK5CYII="
)
ALLOWED_VOICES = frozenset({"M1", "M2", "M3", "M4", "M5", "F1", "F2", "F3", "F4", "F5"})
ALLOWED_RATES = frozenset({"-20%", "-10%", "+0%", "+20%", "+40%", "+60%", "+80%"})
MAX_UPLOAD_BYTES = 900 * 1024 * 1024


def _cleanup_workdir(path: str) -> None:
    shutil.rmtree(path, ignore_errors=True)


async def _execute_job(
    job_id: str,
    work: str,
    chunk_seconds: int,
    voice: str,
    rate: str,
    whisper_model: str,
    *,
    vid_path: Optional[str],
    video_url: str,
    use_demucs: bool = False,
    video_speed: float = 1.0,
    target_lang: str = "tr",
    auto_expressions: bool = False,
) -> None:
    st = JOBS.get(job_id)
    if st is None:
        return
    try:
        st.status = "running"
        st.percent = 1
        st.message = "Başlatılıyor…"

        if not vid_path:
            st.percent = 2
            st.message = "Video indiriliyor"
            vid_path = await asyncio.to_thread(download_youtube, video_url.strip(), work)

        async def report(pct: int, msg: str) -> None:
            j = JOBS.get(job_id)
            if j:
                j.percent = pct
                j.message = msg

        out = await dub_video(
            vid_path,
            work,
            transcribe_audio,
            translate_text,
            text_to_speech,
            chunk_seconds=chunk_seconds,
            voice=voice,
            rate=rate,
            whisper_model=whisper_model,
            progress=report,
            use_demucs=use_demucs,
            video_speed=video_speed,
            target_lang=target_lang,
            auto_expressions=auto_expressions,
        )
        st.output_path = out
        st.percent = 100
        st.message = "Hazır — indirebilirsiniz."
        st.status = "done"
        print(f"[job {job_id[:8]}] Bitti — cikti: {out}")
    except Exception as e:
        import traceback
        err_detail = traceback.format_exc()
        if job_id in JOBS:
            st = JOBS[job_id]
            st.status = "error"
            st.error = f"{str(e)}\n{err_detail[-500:]}"
            st.message = "İşlem başarısız."
        print(f"[job {job_id[:8]}] KRITIK HATA: {e}")
        print(err_detail)
        _cleanup_workdir(work)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    return Response(content=_FAVICON_PNG, media_type="image/png")


@app.get("/")
async def serve_ui():
    index = WEB_DIR / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=404, detail="frontend/index.html bulunamadi")
    return FileResponse(index)


@app.get("/__yt_tr_ping")
async def yt_tr_ping():
    """Statik sunucu / yanlis process ayiklama — burasi JSON donmuyorsa FastAPI calismiyordur."""
    return {"ok": True, "service": "youtube-tr-ceviri-backend", "version": "2.0.0"}


@app.get("/api/info")
async def api_info():
    return {
        "message": "YouTube TR Çeviri API (Hızlı Mod)",
        "version": "2.0.0",
        "openapi_docs": "/docs",
        "endpoints": {
            "/health": "Sağlık kontrolü",
            "/process": "Ses dosyasÄ± işleme (POST) — eklenti",
            "/api/process-full": "Tam video dublaj (POST, tek yanıt MP4)",
            "/api/jobs": "İş oluştur (POST, multipart — Request ile)",
            "/api/dub/start-url": "İş oluştur (POST JSON) — YouTube URL için önerilen",
            "/api/dub/start-upload": "İş oluştur (POST multipart dosya)",
            "/api/routes-debug": "Yüklü rotalar (GET)",
        },
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Sunucu çalışıyor", "mode": "fast"}


@app.post("/process")
async def process_audio(
    file: UploadFile = File(...),
    rate: str = Form("+0%"),
    whisper_model: str = Form("medium"),
    target_lang: str = Form("tr"),
    auto_expressions: bool = Form(False),
):
    """
    Ses → Metin → Çeviri → Ses pipeline.
    rate: TTS konuşma hızı ("+0%" normal, "+40%" hızlı, "+80%" çok hızlı)
    """
    start_time = time.time()

    try:
        audio_bytes = await file.read()

        if len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="BoÅŸ ses dosyasÄ±")

        print(f"\n{'='*50}")
        print(f"Ses alindi: {len(audio_bytes)} bytes")

        t1 = time.time()
        english_text = transcribe_audio(audio_bytes, whisper_model)
        t2 = time.time()
        print(f"Whisper: {t2-t1:.1f}s")

        if not english_text.strip():
            return JSONResponse(
                content={
                    "audio": "",
                    "text": "",
                    "english": "",
                    "duration": round(time.time() - start_time, 2),
                    "message": "KonuÅŸma algÄ±lanamadÄ±",
                }
            )

        t3 = time.time()
        turkish_text = translate_text(english_text, target=target_lang)
        t4 = time.time()
        print(f"Ceviri: {t4-t3:.1f}s")

        t5 = time.time()
        audio_base64 = await text_to_speech(turkish_text, rate=rate, lang=target_lang, auto_expressions=auto_expressions)
        t6 = time.time()
        print(f"TTS: {t6-t5:.1f}s")

        duration = round(time.time() - start_time, 2)
        print(f"Toplam: {duration}s")
        print(f"{'='*50}\n")

        return JSONResponse(
            content={
                "audio": audio_base64,
                "text": turkish_text,
                "english": english_text,
                "duration": duration,
            }
        )

    except Exception as e:
        print(f"Hata: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/process-full")
async def process_full_video(
    file: Optional[UploadFile] = File(None),
    video_url: str = Form(""),
    rate: str = Form("+0%"),
    voice: str = Form("M1"),
    chunk_seconds: int = Form(28),
    whisper_model: str = Form("medium"),
    use_demucs: bool = Form(False),
    video_speed: float = Form(1.0),
    target_lang: str = Form("tr"),
    auto_expressions: bool = Form(False),
):
    """
    Yerel video veya YouTube baglantisindan tam dublaj MP4 uretir.
    """
    if rate not in ALLOWED_RATES:
        rate = "+0%"
    if voice not in ALLOWED_VOICES:
        voice = "M1"
    chunk_seconds = max(12, min(60, int(chunk_seconds)))

    fn = (file.filename or "").strip() if file else ""
    has_file = bool(fn)
    url_clean = (video_url or "").strip()

    if not has_file and not url_clean:
        raise HTTPException(status_code=400, detail="Video dosyasÄ± veya baÄŸlantÄ± gerekli.")
    if has_file and url_clean:
        raise HTTPException(
            status_code=400,
            detail="Sadece dosya yÃ¼kleyin ya da sadece baÄŸlantÄ± girin (ikisini birden deÄŸil).",
        )

    work = tempfile.mkdtemp(prefix="yt_tr_dub_")

    try:
        if has_file:
            assert file is not None
            suf = Path(fn).suffix.lower() or ".mp4"
            if suf not in {".mp4", ".webm", ".mkv", ".mov", ".avi", ".mpeg", ".mpg", ".m4v"}:
                suf = ".mp4"
            vid_path = os.path.join(work, f"giris{suf}")
            content = await file.read()
            if len(content) == 0:
                raise HTTPException(status_code=400, detail="BoÅŸ dosya")
            if len(content) > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=400, detail="Dosya Ã§ok bÃ¼yÃ¼k (limit ~900 MB)")
            Path(vid_path).write_bytes(content)
        else:
            vid_path = await asyncio.to_thread(download_youtube, url_clean, work)

        out_path = await dub_video(
            vid_path,
            work,
            transcribe_audio,
            translate_text,
            text_to_speech,
            chunk_seconds=chunk_seconds,
            voice=voice,
            rate=rate,
            whisper_model=whisper_model,
            use_demucs=use_demucs,
            video_speed=video_speed,
            target_lang=target_lang,
            auto_expressions=auto_expressions,
        )

        return FileResponse(
            out_path,
            media_type="video/mp4",
            filename="dublaj.mp4",
            background=BackgroundTask(_cleanup_workdir, work),
        )
    except HTTPException:
        _cleanup_workdir(work)
        raise
    except Exception as e:
        _cleanup_workdir(work)
        raise HTTPException(status_code=500, detail=str(e)) from e


class DubStartUrlJson(BaseModel):
    """YouTube / URL sekmesi — JSON (multipart + bos File alanlari bazi ortamlarda 404 verebiliyor)."""

    video_url: str = Field(..., min_length=4)
    rate: str = "+0%"
    voice: str = "M1"
    chunk_seconds: int = 28
    whisper_model: str = "medium"
    use_demucs: bool = False
    video_speed: float = 1.0
    target_lang: str = "tr"
    auto_expressions: bool = False


def _normalize_dub_form(rate: str, voice: str, chunk_seconds: int) -> tuple[str, str, int]:
    if rate not in ALLOWED_RATES:
        rate = "+0%"
    if voice not in ALLOWED_VOICES:
        voice = "M1"
    return rate, voice, max(12, min(60, int(chunk_seconds)))


async def _enqueue_dub_job(
    *,
    has_file: bool,
    file_bytes: Optional[bytes],
    original_filename: str,
    url_clean: str,
    rate: str,
    voice: str,
    chunk_seconds: int,
    whisper_model: str,
    use_demucs: bool = False,
    video_speed: float = 1.0,
    target_lang: str = "tr",
    auto_expressions: bool = False,
) -> dict[str, str]:
    if not has_file and not url_clean:
        raise HTTPException(status_code=400, detail="Video dosyasÄ± veya baÄŸlantÄ± gerekli.")
    if has_file and url_clean:
        raise HTTPException(
            status_code=400,
            detail="Sadece dosya yÃ¼kleyin ya da sadece baÄŸlantÄ± girin (ikisini birden deÄŸil).",
        )

    prune_old_jobs()
    job_id = str(uuid.uuid4())
    work = tempfile.mkdtemp(prefix="yt_tr_dub_")
    JOBS[job_id] = JobState(work_dir=work, message="Kuyruktaâ€¦", percent=0)

    try:
        vid_path: Optional[str] = None
        if has_file:
            fn = (original_filename or "").strip() or "video.mp4"
            suf = Path(fn).suffix.lower() or ".mp4"
            if suf not in {".mp4", ".webm", ".mkv", ".mov", ".avi", ".mpeg", ".mpg", ".m4v"}:
                suf = ".mp4"
            vid_path = os.path.join(work, f"giris{suf}")
            if not file_bytes or len(file_bytes) == 0:
                raise HTTPException(status_code=400, detail="BoÅŸ dosya")
            if len(file_bytes) > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=400, detail="Dosya Ã§ok bÃ¼yÃ¼k (limit ~900 MB)")
            Path(vid_path).write_bytes(file_bytes)

        asyncio.create_task(
            _execute_job(
                job_id,
                work,
                chunk_seconds,
                voice,
                rate,
                whisper_model,
                vid_path=vid_path,
                video_url=url_clean if not has_file else "",
                use_demucs=use_demucs,
                video_speed=video_speed,
                target_lang=target_lang,
                auto_expressions=auto_expressions,
            )
        )
        print(f"[job {job_id[:8]}] Kuyruga alindi")
        return {"job_id": job_id}
    except HTTPException:
        JOBS.pop(job_id, None)
        _cleanup_workdir(work)
        raise
    except Exception:
        JOBS.pop(job_id, None)
        _cleanup_workdir(work)
        raise


@app.post("/api/dub/start-url")
async def dub_start_url_json(body: DubStartUrlJson):
    """URL / YouTube — sadece JSON; tarayicidan guvenilir."""
    rate, voice, chunk_seconds = _normalize_dub_form(body.rate, body.voice, body.chunk_seconds)
    url_clean = body.video_url.strip()
    return await _enqueue_dub_job(
        has_file=False,
        file_bytes=None,
        original_filename="",
        url_clean=url_clean,
        rate=rate,
        voice=voice,
        chunk_seconds=chunk_seconds,
        whisper_model=body.whisper_model,
        use_demucs=body.use_demucs,
        video_speed=body.video_speed,
        target_lang=body.target_lang,
        auto_expressions=body.auto_expressions,
    )


@app.post("/api/dub/start-upload")
async def dub_start_upload(
    file: UploadFile = File(...),
    rate: str = Form("+0%"),
    voice: str = Form("M1"),
    chunk_seconds: int = Form(28),
    whisper_model: str = Form("medium"),
    use_demucs: bool = Form(False),
    video_speed: float = Form(1.0),
    target_lang: str = Form("tr"),
    auto_expressions: bool = Form(False),
):
    """Dosya yukleme — zorunlu UploadFile (FormData)."""
    rate, voice, chunk_seconds = _normalize_dub_form(rate, voice, chunk_seconds)
    fn = (file.filename or "").strip()
    if not fn:
        raise HTTPException(status_code=400, detail="Dosya adÄ± gerekli.")
    content = await file.read()
    return await _enqueue_dub_job(
        has_file=True,
        file_bytes=content,
        original_filename=fn,
        url_clean="",
        rate=rate,
        voice=voice,
        chunk_seconds=chunk_seconds,
        whisper_model=whisper_model,
        use_demucs=use_demucs,
        video_speed=video_speed,
        target_lang=target_lang,
        auto_expressions=auto_expressions,
    )


@app.post("/api/jobs")
async def create_dub_job(request: Request):
    """
    Eski yol: tum form alanlarini Request uzerinden okur.
    (Optional UploadFile + Form birlikte bazi surumlerde POST rotasinin hic eslesmemesine yol acabiliyor.)
    """
    form = await request.form()
    video_url = str(form.get("video_url") or "").strip()
    rate = str(form.get("rate") or "+0%")
    voice = str(form.get("voice") or "M1")
    chunk_raw = form.get("chunk_seconds")
    try:
        chunk_seconds = int(chunk_raw) if chunk_raw is not None and str(chunk_raw).strip() != "" else 28
    except (TypeError, ValueError):
        chunk_seconds = 28
    rate, voice, chunk_seconds = _normalize_dub_form(rate, voice, chunk_seconds)
    whisper_model = str(form.get("whisper_model") or "medium").strip()
    use_demucs = str(form.get("use_demucs") or "false").lower() == "true"
    target_lang = str(form.get("target_lang") or "tr")
    auto_expressions = str(form.get("auto_expressions") or "false").lower() == "true"
    try:
        video_speed = float(form.get("video_speed") or 1.0)
    except:
        video_speed = 1.0

    raw_file = form.get("file")
    file_bytes: Optional[bytes] = None
    fn = ""
    if raw_file is not None and hasattr(raw_file, "read"):
        assert isinstance(raw_file, UploadFile)
        fn = (raw_file.filename or "").strip()
        file_bytes = await raw_file.read()

    return await _enqueue_dub_job(
        has_file=bool(fn),
        file_bytes=file_bytes,
        original_filename=fn,
        url_clean=video_url,
        rate=rate,
        voice=voice,
        chunk_seconds=chunk_seconds,
        whisper_model=whisper_model,
        use_demucs=use_demucs,
        video_speed=video_speed,
        target_lang=target_lang,
        auto_expressions=auto_expressions,
    )


@app.get("/api/routes-debug")
async def routes_debug():
    """Hangi rotalar yuklu — 404 ayiklama."""
    out: list[dict[str, Any]] = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            out.append({"path": route.path, "methods": sorted(route.methods)})
    out.sort(key=lambda x: (x["path"], x["methods"]))
    return {"routes": out, "hint": "POST /api/dub/start-url ve /api/jobs burada gorunmeli"}


@app.get("/api/jobs/{job_id}/download")
async def download_job_file(job_id: str):
    st = JOBS.get(job_id)
    if st is None or st.status != "done" or not st.output_path:
        raise HTTPException(status_code=400, detail="Dosya henÃ¼z hazÄ±r deÄŸil.")
    path = st.output_path
    work = st.work_dir

    def _after_send() -> None:
        shutil.rmtree(work, ignore_errors=True)
        JOBS.pop(job_id, None)

    return FileResponse(
        path,
        media_type="video/mp4",
        filename="dublaj.mp4",
        background=BackgroundTask(_after_send),
    )


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    st = JOBS.get(job_id)
    if st is None:
        raise HTTPException(status_code=404, detail="Ä°ÅŸ bulunamadÄ±.")
    return {
        "status": st.status,
        "percent": st.percent,
        "message": st.message,
        "error": st.error,
    }


if __name__ == "__main__":
    import uvicorn

    backend_dir = Path(__file__).resolve().parent
    os.chdir(backend_dir)
    log_level = os.environ.get("YT_TR_LOG", "info").lower()
    try:
        port = int(os.environ.get("YT_TR_PORT", "8000"))
    except ValueError:
        port = 8000

    use_reload = os.environ.get("YT_TR_RELOAD", "").strip().lower() in ("1", "true", "yes", "on")

    print(f"[baslangic] Calisma dizini: {backend_dir}")
    print(f"[baslangic] Port: {port}")
    print(f"[baslangic] Panel: http://127.0.0.1:{port}/")
    print(f"[baslangic] Ping: http://127.0.0.1:{port}/__yt_tr_ping (JSON gelmeli)")
    print(f"[baslangic] Swagger: http://127.0.0.1:{port}/docs")
    if use_reload:
        print("[baslangic] YT_TR_RELOAD=1 — uvicorn reload acik (gelistirici modu)")
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=port,
            reload=True,
            reload_dirs=[str(backend_dir)],
            log_level=log_level,
            access_log=True,
        )
    else:
        print("[baslangic] reload KAPALI — bu dosyadaki 'app' dogrudan calisir (404 rotasi sorunlarini onler).")
        print("[baslangic] Kod degisince sunucuyu Ctrl+C ile yeniden baslatin. Reload icin: YT_TR_RELOAD=1")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            reload=False,
            log_level=log_level,
            access_log=True,
        )
