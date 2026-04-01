import os
import tempfile
import streamlit as st
from openai import OpenAI

SUPPORTED_LANGUAGES = {
    "Korean": "Korean",
    "English": "English",
    "Japanese": "Japanese",
    "Chinese": "Chinese (Simplified)",
    "French": "French",
    "Spanish": "Spanish",
    "German": "German",
}

SUPPORTED_FORMATS = ["mp3", "wav", "m4a", "webm", "mp4", "mpeg", "mpga", "oga"]


def get_openai_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


def transcribe_audio(client: OpenAI, audio_file_path: str) -> str:
    with open(audio_file_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="text",
        )
    return result


def translate_text(client: OpenAI, text: str, target_language: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    f"Translate the following text to {target_language}. "
                    "Return only the translated text without any explanation."
                ),
            },
            {"role": "user", "content": text},
        ],
    )
    return response.choices[0].message.content


def main():
    st.set_page_config(
        page_title="Catchup AI Translator",
        page_icon="🎙️",
        layout="wide",
    )
    st.title("🎙️ Catchup AI Translator")
    st.caption("음성 파일을 텍스트로 변환하고 원하는 언어로 번역합니다.")

    # Sidebar
    with st.sidebar:
        st.header("설정")

        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=os.environ.get("OPENAI_API_KEY", ""),
            placeholder="sk-...",
            help="OpenAI API 키를 입력하세요. 환경변수 OPENAI_API_KEY가 설정된 경우 자동으로 불러옵니다.",
        )

        st.divider()

        target_language = st.selectbox(
            "번역 대상 언어",
            options=list(SUPPORTED_LANGUAGES.keys()),
            index=0,
        )

    # Main area
    uploaded_file = st.file_uploader(
        "오디오 파일을 업로드하세요",
        type=SUPPORTED_FORMATS,
        help=f"지원 형식: {', '.join(SUPPORTED_FORMATS)}",
    )

    if uploaded_file is None:
        st.info("오디오 파일을 업로드하면 자동으로 변환 및 번역이 시작됩니다.")
        return

    if not api_key:
        st.error("OpenAI API 키를 사이드바에 입력해주세요.")
        return

    client = get_openai_client(api_key)

    col1, col2 = st.columns(2)

    # Step 1: Transcription
    with col1:
        st.subheader("📝 원본 텍스트 (STT)")

    with col2:
        st.subheader(f"🌐 번역 결과 ({target_language})")

    transcribed_text = None
    translated_text = None

    # Save uploaded file to a temp file and transcribe
    suffix = "." + uploaded_file.name.rsplit(".", 1)[-1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    try:
        with col1:
            with st.spinner("음성을 텍스트로 변환 중..."):
                transcribed_text = transcribe_audio(client, tmp_path)
            st.text_area(
                label="변환된 텍스트",
                value=transcribed_text,
                height=300,
                label_visibility="collapsed",
            )
            st.download_button(
                label="원본 텍스트 다운로드",
                data=transcribed_text,
                file_name="transcription.txt",
                mime="text/plain",
            )

        with col2:
            with st.spinner("번역 중..."):
                translated_text = translate_text(
                    client, transcribed_text, SUPPORTED_LANGUAGES[target_language]
                )
            st.text_area(
                label="번역 결과",
                value=translated_text,
                height=300,
                label_visibility="collapsed",
            )
            st.download_button(
                label="번역 텍스트 다운로드",
                data=translated_text,
                file_name="translation.txt",
                mime="text/plain",
            )

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    main()
