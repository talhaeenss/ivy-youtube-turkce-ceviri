import sys
import torchaudio
import soundfile as sf

def _mock_save(path, tensor, sample_rate, encoding=None, bits_per_sample=None, **kwargs):
    wav = tensor.t().cpu().numpy()
    if encoding == "PCM_F":
        subtype = "FLOAT"
    else:
        subtype = "PCM_16"
    sf.write(str(path), wav, sample_rate, subtype=subtype)

# Monkey-patch internal torchaudio save to use soundfile
torchaudio.save = _mock_save

from demucs.separate import main
# sys.argv is [patch_demucs.py, ...]
# we need it to look like [demucs, ...]
sys.argv[0] = "demucs"
sys.exit(main())
