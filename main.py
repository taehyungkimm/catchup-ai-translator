import os
import tempfile
import streamlit as st
from openai import OpenAI, AuthenticationError, APIError
from audio_recorder_streamlit import audio_recorder

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_AUDIO_FORMATS = ["mp3", "wav", "m4a", "webm", "mp4", "mpeg", "mpga", "oga"]

# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def build_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


def resolve_target_language(detected_lang: str) -> str:
    """영어 입력이면 한국어로, 그 외 언어면 영어로 번역 대상 결정"""
    return "Korean" if detected_lang.lower() in ("english", "en") else "English"


def detect_language(client: OpenAI, text: str) -> str:
    """GPT로 텍스트 언어 감지 → 언어명 반환 (예: 'Korean', 'English')"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Detect the language of the following text. "
                    "Reply with only the language name in English (e.g. Korean, English, Japanese). "
                    "Do not include any other text."
                ),
            },
            {"role": "user", "content": text[:500]},  # 앞 500자만 사용
        ],
        temperature=0,
    )
    return response.choices[0].message.content.strip()


def transcribe(client: OpenAI, file_path: str):
    """Whisper API로 오디오 → 텍스트 변환 (verbose_json: 언어 감지 포함)"""
    with open(file_path, "rb") as f:
        return client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
        )


def text_to_speech(client: OpenAI, text: str, target_language: str) -> bytes:
    """OpenAI TTS API로 텍스트 → 음성 변환, mp3 bytes 반환"""
    # 한국어는 nova, 영어는 alloy 음성 사용
    voice = "nova" if target_language.lower() == "korean" else "alloy"
    response = client.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=text,
        response_format="mp3",
    )
    return response.content


def translate(client: OpenAI, text: str, target_language: str) -> str:
    """GPT-4o-mini로 텍스트 번역"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are a professional translator. "
                    f"Translate the following text to {target_language}. "
                    "Return only the translated text without any explanation or commentary."
                ),
            },
            {"role": "user", "content": text},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def render_sidebar() -> str:
    with st.sidebar:
        st.header("⚙️ 설정")

        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=os.environ.get("OPENAI_API_KEY", ""),
            placeholder="sk-...",
            help="환경변수 OPENAI_API_KEY가 설정된 경우 자동으로 불러옵니다.",
        )

        st.divider()
        st.info("🔄 **자동 번역 방향**\n\n영어 입력 → 한국어\n\n그 외 언어 입력 → 영어")
        st.divider()
        st.caption("Powered by OpenAI Whisper & GPT-4o-mini")

    return api_key


def show_result(original_text: str, detected_lang: str, translated_text: str, target_lang: str):
    col1, col2 = st.columns(2)

    with col1:
        lang_tag = f" · 감지된 언어: `{detected_lang}`" if detected_lang else ""
        st.subheader(f"📝 원본 텍스트{lang_tag}")
        st.text_area(
            label="원본",
            value=original_text,
            height=320,
            label_visibility="collapsed",
        )
        st.download_button(
            label="원본 텍스트 다운로드",
            data=original_text,
            file_name="transcription.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with col2:
        st.subheader(f"🌐 번역 결과 ({target_lang})")
        st.text_area(
            label="번역",
            value=translated_text,
            height=320,
            label_visibility="collapsed",
        )
        st.download_button(
            label="번역 텍스트 다운로드",
            data=translated_text,
            file_name="translation.txt",
            mime="text/plain",
            use_container_width=True,
        )


# ---------------------------------------------------------------------------
# Tab handlers
# ---------------------------------------------------------------------------

def tab_audio(client: OpenAI):
    """마이크 녹음 → STT → 언어 자동 감지 → 번역"""
    st.write("마이크 버튼을 눌러 녹음을 시작하고, 다시 누르면 종료됩니다.")

    audio_bytes = audio_recorder(
        text="",
        recording_color="#e8484a",
        neutral_color="#6aa36f",
        icon_name="microphone",
        icon_size="3x",
        pause_threshold=3.0,
    )

    if audio_bytes is None:
        st.info("마이크 버튼을 클릭해 녹음을 시작하세요.")
        return

    cache_key = hash(audio_bytes)
    if st.session_state.get("audio_cache_key") == cache_key:
        show_result(
            st.session_state["transcribed_text"],
            st.session_state["detected_lang"],
            st.session_state["translated_text"],
            st.session_state["target_lang"],
        )
        return

    st.audio(audio_bytes, format="audio/wav")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with st.spinner("음성을 텍스트로 변환 중..."):
            result = transcribe(client, tmp_path)
            transcribed_text = result.text
            detected_lang = getattr(result, "language", "")  # Whisper가 감지한 언어

        target_lang = resolve_target_language(detected_lang)

        with st.spinner(f"번역 중... ({detected_lang} → {target_lang})"):
            translated_text = translate(client, transcribed_text, target_lang)

        st.session_state["audio_cache_key"] = cache_key
        st.session_state["transcribed_text"] = transcribed_text
        st.session_state["detected_lang"] = detected_lang
        st.session_state["translated_text"] = translated_text
        st.session_state["target_lang"] = target_lang

        show_result(transcribed_text, detected_lang, translated_text, target_lang)

    except AuthenticationError:
        st.error("API 키가 유효하지 않습니다. 사이드바에서 올바른 키를 입력해주세요.")
    except APIError as e:
        st.error(f"OpenAI API 오류: {e}")
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
    finally:
        os.unlink(tmp_path)


def tab_voice_to_text(client: OpenAI):
    """마이크 녹음 → STT → 언어 자동 감지 → 번역 텍스트 출력"""
    st.write("마이크 버튼을 눌러 녹음을 시작하고, 다시 누르면 종료됩니다.")
    st.caption("한국어 → 영어 / 영어 → 한국어 / 그 외 언어 → 영어")

    audio_bytes = audio_recorder(
        text="",
        recording_color="#e8484a",
        neutral_color="#4a90d9",
        icon_name="microphone",
        icon_size="3x",
        pause_threshold=3.0,
    )

    if audio_bytes is None:
        st.info("마이크 버튼을 클릭해 녹음을 시작하세요.")
        return

    cache_key = f"v2t_{hash(audio_bytes)}"
    if st.session_state.get("v2t_cache_key") == cache_key:
        _render_voice_to_text_result(
            st.session_state["v2t_detected_lang"],
            st.session_state["v2t_transcribed"],
            st.session_state["v2t_translated"],
            st.session_state["v2t_target_lang"],
        )
        return

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with st.spinner("음성을 텍스트로 변환 중..."):
            result = transcribe(client, tmp_path)
            transcribed_text = result.text
            detected_lang = getattr(result, "language", "")

        target_lang = resolve_target_language(detected_lang)

        with st.spinner(f"번역 중... ({detected_lang} → {target_lang})"):
            translated_text = translate(client, transcribed_text, target_lang)

        st.session_state["v2t_cache_key"] = cache_key
        st.session_state["v2t_detected_lang"] = detected_lang
        st.session_state["v2t_transcribed"] = transcribed_text
        st.session_state["v2t_translated"] = translated_text
        st.session_state["v2t_target_lang"] = target_lang

        _render_voice_to_text_result(detected_lang, transcribed_text, translated_text, target_lang)

    except AuthenticationError:
        st.error("API 키가 유효하지 않습니다. 사이드바에서 올바른 키를 입력해주세요.")
    except APIError as e:
        st.error(f"OpenAI API 오류: {e}")
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
    finally:
        os.unlink(tmp_path)


def _render_voice_to_text_result(
    detected_lang: str, transcribed_text: str, translated_text: str, target_lang: str
):
    st.success(f"감지된 언어: **{detected_lang}** → 번역 언어: **{target_lang}**")

    st.subheader("🌐 번역 결과")
    st.text_area(
        label="번역 결과",
        value=translated_text,
        height=250,
        label_visibility="collapsed",
    )
    st.download_button(
        label="번역 텍스트 다운로드",
        data=translated_text,
        file_name="translated.txt",
        mime="text/plain",
        use_container_width=True,
    )

    with st.expander("원본 음성 텍스트 보기"):
        st.text(transcribed_text)


def tab_voice_to_voice(client: OpenAI):
    """마이크 녹음 → STT → 언어 자동 감지 → 번역 → TTS 음성 출력"""
    st.write("마이크 버튼을 눌러 녹음을 시작하고, 다시 누르면 종료됩니다.")
    st.caption("한국어 → 영어 음성 / 영어 → 한국어 음성 / 그 외 언어 → 영어 음성")

    audio_bytes = audio_recorder(
        text="",
        recording_color="#e8484a",
        neutral_color="#9b59b6",
        icon_name="microphone",
        icon_size="3x",
        pause_threshold=3.0,
    )

    if audio_bytes is None:
        st.info("마이크 버튼을 클릭해 녹음을 시작하세요.")
        return

    cache_key = f"v2v_{hash(audio_bytes)}"
    if st.session_state.get("v2v_cache_key") == cache_key:
        _render_voice_to_voice_result(
            st.session_state["v2v_detected_lang"],
            st.session_state["v2v_transcribed"],
            st.session_state["v2v_translated"],
            st.session_state["v2v_target_lang"],
            st.session_state["v2v_tts_bytes"],
        )
        return

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with st.spinner("음성을 텍스트로 변환 중..."):
            result = transcribe(client, tmp_path)
            transcribed_text = result.text
            detected_lang = getattr(result, "language", "")

        target_lang = resolve_target_language(detected_lang)

        with st.spinner(f"번역 중... ({detected_lang} → {target_lang})"):
            translated_text = translate(client, transcribed_text, target_lang)

        with st.spinner("번역된 텍스트를 음성으로 변환 중..."):
            tts_bytes = text_to_speech(client, translated_text, target_lang)

        st.session_state["v2v_cache_key"] = cache_key
        st.session_state["v2v_detected_lang"] = detected_lang
        st.session_state["v2v_transcribed"] = transcribed_text
        st.session_state["v2v_translated"] = translated_text
        st.session_state["v2v_target_lang"] = target_lang
        st.session_state["v2v_tts_bytes"] = tts_bytes

        _render_voice_to_voice_result(
            detected_lang, transcribed_text, translated_text, target_lang, tts_bytes
        )

    except AuthenticationError:
        st.error("API 키가 유효하지 않습니다. 사이드바에서 올바른 키를 입력해주세요.")
    except APIError as e:
        st.error(f"OpenAI API 오류: {e}")
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
    finally:
        os.unlink(tmp_path)


def _render_voice_to_voice_result(
    detected_lang: str,
    transcribed_text: str,
    translated_text: str,
    target_lang: str,
    tts_bytes: bytes,
):
    st.success(f"감지된 언어: **{detected_lang}** → 번역 언어: **{target_lang}**")

    st.subheader("🔊 번역된 음성")
    st.audio(tts_bytes, format="audio/mp3", autoplay=True)
    st.download_button(
        label="번역 음성 다운로드 (mp3)",
        data=tts_bytes,
        file_name="translated_voice.mp3",
        mime="audio/mpeg",
        use_container_width=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        with st.expander("원본 음성 텍스트 보기"):
            st.text(transcribed_text)
    with col2:
        with st.expander("번역 텍스트 보기"):
            st.text(translated_text)


def tab_text(client: OpenAI):
    """텍스트 직접 입력 → 언어 자동 감지 → 번역"""
    input_text = st.text_area(
        "번역할 텍스트를 입력하세요",
        height=200,
        placeholder="번역하고 싶은 텍스트를 여기에 입력하세요...",
    )

    if st.button("번역하기", type="primary", use_container_width=True):
        if not input_text.strip():
            st.warning("텍스트를 입력해주세요.")
            return

        try:
            with st.spinner("언어 감지 중..."):
                detected_lang = detect_language(client, input_text)

            target_lang = resolve_target_language(detected_lang)

            with st.spinner(f"번역 중... ({detected_lang} → {target_lang})"):
                translated_text = translate(client, input_text, target_lang)

            show_result(input_text, detected_lang, translated_text, target_lang)

        except AuthenticationError:
            st.error("API 키가 유효하지 않습니다. 사이드바에서 올바른 키를 입력해주세요.")
        except APIError as e:
            st.error(f"OpenAI API 오류: {e}")
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title="Catchup AI Translator",
        page_icon="🎙️",
        layout="wide",
    )
    st.title("🎙️ Catchup AI Translator")
    st.caption("영어로 말하거나 입력하면 한국어로, 그 외 언어는 영어로 자동 번역합니다.")

    api_key = render_sidebar()

    if not api_key:
        st.warning("사이드바에서 OpenAI API 키를 입력해주세요.")
        return

    client = build_client(api_key)

    audio_tab, text_tab, voice_text_tab, voice_voice_tab = st.tabs([
        "🎵 음성 번역",
        "✏️ 텍스트 번역",
        "🔊 음성 → 텍스트",
        "🗣️ 음성 → 음성",
    ])

    with audio_tab:
        tab_audio(client)

    with text_tab:
        tab_text(client)

    with voice_text_tab:
        tab_voice_to_text(client)

    with voice_voice_tab:
        tab_voice_to_voice(client)


if __name__ == "__main__":
    main()
