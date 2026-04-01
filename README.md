# 🎙️ Catchup AI Translator

OpenAI의 Whisper, GPT-4o-mini, TTS-1 API를 활용한 음성 & 텍스트 AI 번역 웹 애플리케이션입니다.  
Streamlit 기반으로 브라우저에서 바로 실행되며, 4가지 번역 모드를 제공합니다.

---

## 주요 기능

| 탭 | 기능 설명 |
|---|---|
| 🎵 음성 번역 | 마이크로 녹음 → STT 변환 → 원문/번역 텍스트 나란히 표시 |
| ✏️ 텍스트 번역 | 텍스트 직접 입력 → 언어 자동 감지 → 번역 결과 표시 |
| 🔊 음성 → 텍스트 | 마이크로 녹음 → 번역된 텍스트만 출력 |
| 🗣️ 음성 → 음성 | 마이크로 녹음 → 번역된 음성으로 자동 재생 |

### 자동 번역 방향

| 입력 언어 | 출력 언어 |
|---|---|
| 영어 | 한국어 |
| 한국어 / 그 외 모든 언어 | 영어 |

---

## 스크린샷

> 앱 실행 후 브라우저에서 확인하세요.

---

## 설치 및 실행

### 1. 저장소 클론

```bash
git clone https://github.com/taehyungkimm/catchup-ai-translator.git
cd catchup-ai-translator
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. OpenAI API 키 설정

환경변수로 설정하거나 앱 실행 후 사이드바에서 직접 입력할 수 있습니다.

```bash
export OPENAI_API_KEY="sk-..."
```

### 4. 앱 실행

```bash
streamlit run main.py
```

브라우저에서 `http://localhost:8501` 로 접속합니다.

---

## 기술 스택

| 항목 | 내용 |
|---|---|
| 언어 | Python 3.9+ |
| 웹 프레임워크 | Streamlit |
| STT | OpenAI Whisper (`whisper-1`) |
| 번역 | OpenAI GPT-4o-mini |
| TTS | OpenAI TTS-1 (`nova`, `alloy`) |
| 마이크 녹음 | audio-recorder-streamlit |

---

## 요구사항

- Python 3.9 이상
- OpenAI API 키 ([발급받기](https://platform.openai.com/api-keys))
- 마이크가 연결된 환경 (음성 기능 사용 시)
- HTTPS 또는 localhost 환경 (브라우저 마이크 접근 허용)

---

## 프로젝트 구조

```
catchup-ai-translator/
├── main.py            # 메인 Streamlit 앱 (4가지 번역 모드)
├── sample.py          # 기본 프로토타입 (파일 업로드 방식)
├── requirements.txt   # 패키지 의존성
├── 요구사항정의서.md   # 프로젝트 요구사항 정의서 (RDD)
└── README.md
```

---

## 라이선스

MIT License
