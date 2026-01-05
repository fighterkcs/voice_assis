import whisper
import soundfile as sf
import numpy as np
import os
import tempfile
import shutil

model = whisper.load_model("tiny")

def _check_ffmpeg_available():
    return shutil.which("ffmpeg") is not None

def _setup_ffmpeg_path():
    if _check_ffmpeg_available():
        return True
    common_paths = [
        r"C:\ffmpeg\bin",
        r"C:\Program Files\ffmpeg\bin",
        r"C:\Program Files (x86)\ffmpeg\bin",
        os.path.join(os.path.expanduser("~"), "ffmpeg", "bin"),
        os.path.join(os.path.expanduser("~"), "AppData", "Local", "ffmpeg", "bin"),
    ]
    for path in common_paths:
        ffmpeg_exe = os.path.join(path, "ffmpeg.exe")
        if os.path.exists(ffmpeg_exe):
            current_path = os.environ.get("PATH", "")
            if path not in current_path:
                os.environ["PATH"] = path + os.pathsep + current_path
            return True
    return False

def transcribe(audio_path):
    if not audio_path or not isinstance(audio_path, str):
        raise ValueError("Invalid audio_path: must be a non-empty string")
    audio_path = os.path.normpath(os.path.abspath(audio_path))
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    if not os.path.isfile(audio_path):
        raise ValueError(f"Path is not a file: {audio_path}")
    if not os.access(audio_path, os.R_OK):
        raise PermissionError(f"Cannot read audio file: {audio_path}")
    if os.path.getsize(audio_path) == 0:
        raise ValueError(f"Audio file is empty: {audio_path}")
    processed_audio_path = None
    try:
        try:
            audio_data, sample_rate = sf.read(audio_path, dtype='float32')
        except Exception as read_error:
            try:
                result = model.transcribe(
                    audio_path, 
                    language=None,
                    initial_prompt="Hinglish conversation mixing Hindi and English naturally."
                )
                return result["text"].strip()
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"Cannot read audio file with soundfile or ffmpeg. "
                    f"Soundfile error: {str(read_error)}. "
                    f"Please ensure audio file is in a supported format (WAV, MP3, etc.)"
                ) from read_error
        audio_data = np.asarray(audio_data, dtype=np.float32)
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1, dtype=np.float32)
        audio_data = audio_data.flatten().astype(np.float32)
        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            audio_data = (audio_data / max_val).astype(np.float32)
        if sample_rate != 16000:
            num_samples = int(len(audio_data) * 16000 / sample_rate)
            indices = np.linspace(0, len(audio_data) - 1, num_samples, dtype=np.float32)
            audio_data = np.interp(
                indices, 
                np.arange(len(audio_data), dtype=np.float32), 
                audio_data
            ).astype(np.float32)
            sample_rate = 16000
        audio_data = np.ascontiguousarray(audio_data, dtype=np.float32)
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        if not audio_data.flags['C_CONTIGUOUS']:
            audio_data = np.ascontiguousarray(audio_data)
        try:
            result = model.transcribe(
                audio_data,
                language=None,
                initial_prompt="Hinglish conversation mixing Hindi and English naturally. Speaker uses both languages interchangeably.",
                task="transcribe",
                temperature=0.0,
                best_of=1,
                beam_size=5
            )
            return result["text"].strip()
        except (TypeError, ValueError, AttributeError, RuntimeError) as array_error:
            fallback_audio_path = None
            try:
                temp_dir = tempfile.gettempdir()
                with tempfile.NamedTemporaryFile(
                    delete=False, 
                    suffix=".wav",
                    dir=temp_dir
                ) as temp_file:
                    fallback_audio_path = temp_file.name
                sf.write(fallback_audio_path, audio_data, sample_rate, format='WAV', subtype='PCM_16')
                if not os.path.exists(fallback_audio_path) or os.path.getsize(fallback_audio_path) == 0:
                    raise RuntimeError("Failed to create processed audio file")
                _setup_ffmpeg_path()
                result = model.transcribe(
                    fallback_audio_path,
                    language=None,
                    initial_prompt="Hinglish conversation mixing Hindi and English naturally."
                )
                return result["text"].strip()
            except FileNotFoundError as ffmpeg_error:
                raise FileNotFoundError(
                    "ffmpeg is required for audio transcription but was not found.\n"
                    "Please install ffmpeg:\n"
                    "1. Download from https://ffmpeg.org/download.html\n"
                    "2. Extract to C:\\ffmpeg\n"
                    "3. Add C:\\ffmpeg\\bin to your system PATH\n"
                    "OR install via: winget install ffmpeg\n"
                    f"Original array error: {str(array_error)}"
                ) from ffmpeg_error
            finally:
                if fallback_audio_path and os.path.exists(fallback_audio_path):
                    try:
                        os.remove(fallback_audio_path)
                    except Exception:
                        pass
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Failed to transcribe audio: {str(e)}. "
            f"Audio file exists at {audio_path} but cannot be processed."
        ) from e
    except Exception as e:
        try:
            result = model.transcribe(
                audio_path,
                language=None,
                initial_prompt="Hinglish conversation mixing Hindi and English naturally."
            )
            return result["text"].strip()
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Transcription failed. Audio file exists but cannot be processed. "
                f"Original error: {str(e)}. "
                f"Ensure audio file is in a valid format (WAV, MP3, etc.)."
            ) from e
        except Exception as fallback_error:
            raise RuntimeError(
                f"Transcription failed: {str(fallback_error)}. "
                f"Original error: {str(e)}"
            ) from fallback_error
    finally:
        if processed_audio_path and os.path.exists(processed_audio_path):
            try:
                os.remove(processed_audio_path)
            except Exception:
                pass
