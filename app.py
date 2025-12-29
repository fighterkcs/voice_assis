import streamlit as st
from audio_recorder_streamlit import audio_recorder
import tempfile
import os
import base64
import time
from stt import transcribe
from llm import krishna_reply
from tts import speak

st.set_page_config(page_title="Krishna Voice Companion", layout="centered", initial_sidebar_state="collapsed")

st.title("Krishna ")
st.caption("Speak naturally in Hinglish - Krishna will respond in voice")

audio = audio_recorder(text="🎤 Speak", pause_threshold=2.0)

if audio:
    temp_dir = tempfile.gettempdir()
    audio_path = None
    tts_audio_path = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=".wav",
            dir=temp_dir,
            mode='wb'
        ) as f:
            f.write(audio)
            f.flush()
            os.fsync(f.fileno())
            audio_path = os.path.normpath(f.name)
        if not os.path.exists(audio_path):
            st.error("❌ Failed to save audio file. Please try again.")
            st.stop()
        if os.path.getsize(audio_path) == 0:
            st.error("❌ Audio file is empty. Please record again.")
            st.stop()
        try:
            with st.spinner("Listening..."):
                text = transcribe(audio_path)
                if not text or not text.strip():
                    st.warning("⚠️ No speech detected. Please try again.")
                    st.stop()
                with st.expander("💬 What you said", expanded=False):
                    st.write(text)
                with st.spinner("Krishna is thinking..."):
                    try:
                        reply = krishna_reply(text)
                        if not reply or not reply.strip():
                            st.warning("⚠️ No response generated. Please try again.")
                            st.stop()
                        with st.expander(" Krishna", expanded=False):
                            st.write(reply)
                        with st.spinner("Speaking..."):
                            try:
                                tts_audio_path = speak(reply)
                                if tts_audio_path and os.path.exists(tts_audio_path):
                                    with open(tts_audio_path, 'rb') as audio_file:
                                        audio_bytes = audio_file.read()
                                    audio_base64 = base64.b64encode(audio_bytes).decode()
                                    audio_id = f"krishna_{int(time.time() * 1000000)}"
                                    audio_html = f"""
                                    <audio id="{audio_id}" autoplay style="display: none;">
                                        <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                                    </audio>
                                    <script>
                                    (function() {{
                                        var audio = document.getElementById('{audio_id}');
                                        if (audio) {{
                                            audio.play().catch(function(e) {{
                                                console.log('Autoplay:', e);
                                            }});
                                        }}
                                    }})();
                                    </script>
                                    """
                                    st.markdown(audio_html, unsafe_allow_html=True)
                                else:
                                    st.warning("⚠️ Audio file not generated.")
                            except Exception as tts_error:
                                st.error(f"❌ Error during text-to-speech: {str(tts_error)}")
                    except Exception as llm_error:
                        st.error(f"❌ Error during AI response generation: {str(llm_error)}")
                        st.info("💡 Please check your API keys and try again.")
        except FileNotFoundError as fnf_error:
            st.error(f"❌ File not found error: {str(fnf_error)}")
            st.info("💡 Please ensure your audio is clear and try again.")
        except Exception as e:
            st.error(f"❌ Error during transcription: {str(e)}")
            st.info("💡 Please ensure your audio is clear and try again.")
        finally:
            try:
                if audio_path and os.path.exists(audio_path):
                    os.remove(audio_path)
            except Exception:
                pass
    except Exception as e:
        st.error(f"❌ Failed to process audio: {str(e)}")
        try:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
            if tts_audio_path and os.path.exists(tts_audio_path):
                os.remove(tts_audio_path)
        except:
            pass
