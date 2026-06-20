"""
Video dosyasindan ses cikarip parca parca dublaj uretir, videoyla muxlar.
"""

from __future__ import annotations

import asyncio
import base64
import glob
import os
import shutil
import subprocess
from collections.abc import Awaitable, Callable
from pathlib import Path

ProgressCb = Callable[[int, str], Awaitable[None]]


def ffmpeg_bin() -> str:
    ff = shutil.which("ffmpeg")
    if ff:
        return ff
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def _run_ffmpeg(args: list[str], cwd: str | None = None) -> None:
    cmd = [ffmpeg_bin()] + args
    # Windows'ta capture_output=True (stdout=PIPE + stderr=PIPE) ile buyuk loglarda kilitlenme (deadlock) olabiliyor.
    # ffmpeg loglari stderr'e yazar, stdout genelde bostur (cikti dosyaya gidiyorsa).
    r = subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
        encoding="utf-8",
        errors="replace"
    )
    if r.returncode != 0:
        tail = (r.stderr or "")[-2500:]
        raise RuntimeError(f"ffmpeg basarisiz: {tail}")


def extract_wav_hq(video_path: str, out_wav: str) -> None:
    _run_ffmpeg(
        ["-y", "-i", video_path, "-ar", "44100", "-ac", "2", "-vn", "-f", "wav", out_wav]
    )


def split_wav_segments(wav_path: str, out_dir: str, chunk_sec: int) -> list[str]:
    # Segment muxer icin pattern. %03d yetersiz kalmamali (999 * 28s = 466dk).
    pattern = os.path.join(out_dir, "seg_%03d.wav")
    os.makedirs(out_dir, exist_ok=True)
    _run_ffmpeg(
        [
            "-y",
            "-i",
            wav_path,
            "-f",
            "segment",
            "-segment_time",
            str(chunk_sec),
            "-reset_timestamps",
            "1",
            pattern,
        ]
    )
    files = sorted(glob.glob(os.path.join(out_dir, "seg_*.wav")))
    if not files:
        raise RuntimeError("Ses parcalanamadi (bos veya desteklenmeyen dosya).")
    return files


def pad_audio_to_duration(in_path: str, out_path: str, duration_sec: float) -> None:
    # apad filtrelenmis sesi dur_sec'e tamamlar. -t ile de fazlasini keseriz.
    _run_ffmpeg(
        [
            "-y",
            "-i",
            in_path,
            "-af",
            f"apad=whole_dur={duration_sec}",
            "-t",
            str(duration_sec),
            out_path,
        ]
    )


def make_silence_mp3(out_path: str, duration_sec: float) -> None:
    dur = max(0.1, duration_sec)
    _run_ffmpeg(
        [
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=24000:cl=mono",
            "-t",
            str(dur),
            "-c:a",
            "libmp3lame",
            "-b:a",
            "64k",
            out_path,
        ]
    )


def concat_mp3_files(mp3_paths: list[str], out_mp3: str, work_dir: str) -> None:
    list_path = os.path.join(work_dir, "concat.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for p in mp3_paths:
            ap = os.path.abspath(p).replace("\\", "/")
            f.write(f"file '{ap}'\n")
    _run_ffmpeg(
        ["-y", "-f", "concat", "-safe", "0", "-i", list_path, "-af", "loudnorm=I=-14:LRA=11:TP=-1.5", "-c:a", "libmp3lame", "-b:a", "128k", out_mp3]
    )


def separate_audio_demucs(audio_path: str, out_dir: str) -> tuple[str, str]:
    import sys
    import os
    import subprocess
    
    patch_script = os.path.join(os.path.dirname(__file__), "patch_demucs.py")
    cmd = [
        sys.executable, patch_script,
        "-n", "htdemucs_ft",
        "--two-stems", "vocals",
        "-o", out_dir,
        audio_path
    ]
    
    print(f"[demucs] Baslatiliyor: {audio_path}")
    # Demucs progress bar'lari stdout/stderr doldurabilir. Stdout kapali tutmak guvenli.
    r = subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        cwd=out_dir,
        encoding="utf-8",
        errors="replace"
    )
    
    if r.returncode != 0:
        err = r.stderr or "Bilinmeyen hata"
        print(f"[demucs] HATA (kod {r.returncode}): {err[-1000:]}")
        raise RuntimeError(f"demucs basarisiz (kod {r.returncode}): {err[-500:]}")
    
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    vocals = os.path.join(out_dir, "htdemucs_ft", base_name, "vocals.wav")
    no_vocals = os.path.join(out_dir, "htdemucs_ft", base_name, "no_vocals.wav")
    
    if not os.path.isfile(vocals) or not os.path.isfile(no_vocals):
        raise RuntimeError("demucs islemi bitti ama cikti dosyalari (vocals/no_vocals) bulunamadi.")
    
    print(f"[demucs] Basarili: {vocals}")
    return vocals, no_vocals


def speed_up_video(in_path: str, out_path: str, speed: float) -> None:
    # Video: setpts=1/speed*PTS
    # Audio: atempo=speed (0.5 - 2.0 arasi destekler)
    if speed <= 1.0:
        import shutil
        shutil.copy2(in_path, out_path)
        return

    _run_ffmpeg(
        [
            "-y",
            "-i", in_path,
            "-filter_complex", f"[0:v]setpts={1.0/speed}*PTS[v];[0:a]atempo={speed}[a]",
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            out_path
        ]
    )


def mux_video_and_audio_mix(video_path: str, bgm_path: str, tts_path: str, out_path: str, use_demucs: bool = False) -> None:
    # use_demucs=False ise arka plan sesini (bg) tamamen kapatiyoruz (0).
    # use_demucs=True ise bg (instrumental) 0.8 civari gayet iyi.
    bg_vol = "0.8" if use_demucs else "0"
    _run_ffmpeg(
        [
            "-y",
            "-i", video_path,
            "-i", bgm_path,
            "-i", tts_path,
            "-filter_complex", f"[1:a]volume={bg_vol}[bg];[2:a]volume=1.5[dub];[bg][dub]amix=inputs=2:duration=longest:dropout_transition=0,volume=2.0[a]",
            "-map", "0:v:0",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            out_path,
        ]
    )


def download_youtube(url: str, out_dir: str) -> str:
    out_tmpl = os.path.join(out_dir, "yt_src.%(ext)s")
    cmd = [
        "yt-dlp",
        "-o",
        out_tmpl,
        "--merge-output-format",
        "mp4",
        "-f",
        "bestvideo+bestaudio/best",
        url,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=out_dir, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"yt-dlp: {(r.stderr or r.stdout or '')[-2000:]}")
    for name in ("yt_src.mp4", "yt_src.webm", "yt_src.mkv"):
        p = os.path.join(out_dir, name)
        if os.path.isfile(p):
            return p
    found = sorted(Path(out_dir).glob("yt_src.*"))
    if found:
        return str(found[0])
    raise RuntimeError("yt-dlp indirdi ama video dosyasi bulunamadi.")


async def _notify(progress: ProgressCb | None, pct: int, msg: str) -> None:
    if progress:
        await progress(max(0, min(100, pct)), msg)


async def dub_video(
    video_path: str,
    work_dir: str,
    transcribe_audio,
    translate_text,
    text_to_speech,
    *,
    chunk_seconds: int,
    voice: str,
    rate: str,
    whisper_model: str = "small",
    progress: ProgressCb | None = None,
    use_demucs: bool = False,
    video_speed: float = 1.0,
    target_lang: str = "tr",
    auto_expressions: bool = False,
) -> str:
    await _notify(progress, 4, "Ses kanalı çıkarılıyor…")
    wav = os.path.join(work_dir, "full.wav")
    await asyncio.to_thread(extract_wav_hq, video_path, wav)

    vocals_wav = wav
    no_vocals_wav = wav

    if use_demucs:
        await _notify(progress, 6, "Sesler ayrıştırılıyor (Demucs)... Bu işlem biraz sürebilir.")
        demucs_out = os.path.join(work_dir, "demucs_out")
        os.makedirs(demucs_out, exist_ok=True)
        vocals_wav, no_vocals_wav = await asyncio.to_thread(separate_audio_demucs, wav, demucs_out)
    else:
        await _notify(progress, 8, "Demucs atlanıyor (Hızlı Mod)...")

    await _notify(progress, 9, "Ses parçalara bölünüyor…")
    seg_dir = os.path.join(work_dir, "wav_chunks")
    segments = await asyncio.to_thread(split_wav_segments, vocals_wav, seg_dir, chunk_seconds)
    total = len(segments)
    if total < 1:
        raise RuntimeError("Ses parçası yok.")

    mp3_files: list[str] = []
    span = 75  # 10 .. 85 arası parça işleri
    base = 10
    for i, seg_path in enumerate(segments):
        pct_lo = base + int((i / total) * span)
        await _notify(
            progress,
            pct_lo,
            f"Parça {i + 1}/{total}: konuşma tanıma ve çeviri…",
        )
        wav_bytes = Path(seg_path).read_bytes()
        en = await asyncio.to_thread(transcribe_audio, wav_bytes, whisper_model)
        tr = ""
        if en and en.strip():
            tr = await asyncio.to_thread(translate_text, en, target_lang)

        await _notify(
            progress,
            base + int(((i + 0.5) / total) * span),
            f"Parça {i + 1}/{total}: Ses sentezleme (TTS)…",
        )

        out_mp3 = os.path.join(work_dir, f"tts_{i:04d}.mp3")
        raw_mp3 = os.path.join(work_dir, f"tts_raw_{i:04d}.mp3")
        if tr and tr.strip():
            b64 = await text_to_speech(tr, voice=voice, rate=rate, lang=target_lang, auto_expressions=auto_expressions)
            if b64:
                raw_data = base64.b64decode(b64)
                await asyncio.to_thread(Path(raw_mp3).write_bytes, raw_data)
                # Süre sabitleme (Padding)
                await asyncio.to_thread(pad_audio_to_duration, raw_mp3, out_mp3, float(chunk_seconds))
            else:
                await asyncio.to_thread(make_silence_mp3, out_mp3, float(chunk_seconds))
        else:
            await asyncio.to_thread(make_silence_mp3, out_mp3, float(chunk_seconds))
        mp3_files.append(out_mp3)

        await _notify(
            progress,
            base + int(((i + 1) / total) * span),
            f"Parça {i + 1}/{total} tamam.",
        )

    await _notify(progress, 86, "TTS parçaları birleştiriliyor…")
    merged = os.path.join(work_dir, "dub_merged.mp3")
    await asyncio.to_thread(concat_mp3_files, mp3_files, merged, work_dir)

    await _notify(progress, 93, "Orijinal müzik/efektlerle Türkçe dublaj birleştiriliyor (mux)…")
    out_video = os.path.join(work_dir, "cikti_dublaj.mp4")
    await asyncio.to_thread(mux_video_and_audio_mix, video_path, no_vocals_wav, merged, out_video, use_demucs)

    if video_speed > 1.0:
        await _notify(progress, 97, f"Video hızı {video_speed}x yapılıyor…")
        final_video = os.path.join(work_dir, "cikti_speed.mp4")
        await asyncio.to_thread(speed_up_video, out_video, final_video, video_speed)
        out_video = final_video

    await _notify(progress, 100, "Tamamlandı.")
    return out_video
