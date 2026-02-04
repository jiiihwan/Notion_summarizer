# 🧠 Notion AI Intelligent Summarizer (노션 AI 자동 요약기)

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Notion API](https://img.shields.io/badge/Notion-API-black.svg)](https://developers.notion.com/)
[![Gemini API](https://img.shields.io/badge/Google%20Gemini-2.0%2F3.0-orange.svg)](https://ai.google.dev/)

**"노션에 쌓여있는 수많은 글들, AI가 대신 읽고 핵심만 요약해줍니다."**

이 프로젝트는 Notion 데이터베이스나 페이지에 있는 방대한 자료들을 자동으로 긁어와서, Google Gemini AI (최신 모델)를 통해 분석하고, 그 결과를 다시 Notion에 예쁜 보고서 형태로 저장해주는 도구입니다.

![Demo](https://via.placeholder.com/800x400.png?text=Notion+AI+Summarizer+Demo) 
*(실행 예시 스크린샷)*

---

## ✨ 주요 기능 (Key Features)

1.  **🔍 심층 탐색 (Deep Recursive Fetching)**
    *   단순히 페이지만 읽지 않습니다. **콜아웃(Callout), 토글(Toggle List), 컬럼** 안에 숨겨진 내용까지 샅샅이 찾아냅니다. (Inline Database 포함)
2.  **📝 스마트 포맷팅 (Markdown to Notion)**
    *   AI가 작성한 요약을 **Notion 전용 블록**(헤더, 인용구, 구분선, 체크리스트 등)으로 깔끔하게 변환하여 저장합니다.
3.  **🤖 지능형 모델 전환 (Smart Fallback)**
    *   최신 모델(`gemini-3.0-flash`)을 우선 사용하되, 사용량이 많아지면 자동으로 안정적인 모델(`gemini-2.5-flash`)로 전환하여 끊김 없이 작동합니다.
4.  **🏷️ 속성 인식 (Property Aware)**
    *   페이지의 **상태(Status), 태그(Tags), 날짜(Date)** 정보까지 AI에게 전달하여 문맥에 맞는 정교한 요약이 가능합니다.
5.  **🎨 사용자 친화적 경험**
    *   대화형 인터페이스(CLI)로 누구나 쉽게 사용 가능합니다.
    *   자동 ID 보정 기능으로 복잡한 URL을 그냥 붙여넣어도 알아서 인식합니다.

---

## 🛠️ 시작하기 (Getting Started)

### 1. 사전 준비 (Prerequisites)
이 프로그램을 사용하려면 두 가지 API 키가 필요합니다.

*   **Notion Integration Token**: [Notion My Integrations](https://www.notion.so/my-integrations)에서 새 통합을 만들고 '프라이빗 API 토큰'을 발급받으세요.
    *   *(주의: 요약하려는 페이지/데이터베이스에 '연결(Connections)' 메뉴를 통해 이 통합을 추가해줘야 합니다!)*
*   **Google Gemini API Key**: [Google AI Studio](https://aistudio.google.com/app/apikey)에서 무료로 발급받을 수 있습니다.

### 2. 설치 (Installation)

```bash
# 1. 프로젝트 다운로드 (Git Clone)
git clone https://github.com/your-username/notion-ai-summarizer.git
cd notion-ai-summarizer

# 2. 가상환경 생성 (권장)
python -m venv venv
# 윈도우:
.\venv\Scripts\activate
# 맥/리눅스:
source venv/bin/activate

# 3. 필수 라이브러리 설치
pip install -r requirements.txt
```

### 3. 환경 설정 (.env)
프로젝트 폴더 안에 `.env` 파일을 새로 만들고, 아래 내용을 복사해서 채워넣으세요.

```ini
# .env 파일 내용

# 1. Notion API 토큰
NOTION_TOKEN=ntn_... (발급받은 토큰)

# 2. 요약할 대상의 ID (데이터베이스 또는 페이지)
# URL의 맨 뒤 32자리 숫자+영어 코드만 넣으시면 됩니다.
NOTION_DATABASE_ID=your_page_or_database_id

# 3. Google Gemini API 키
GEMINI_API_KEY=AIza... (발급받은 키)
```

> **Tip**: `NOTION_DATABASE_ID`에는 Notion 페이지 URL을 통째로 넣지 말고, `?` 앞부분의 **32자리 ID**만 복사해서 넣는 것이 가장 정확합니다. (어느 정도 자동 보정 기능은 내장되어 있습니다.)

---

## 🚀 사용 방법 (Usage)

설정이 끝났다면 이제 실행만 하면 됩니다!

### 윈도우 사용자
폴더 안에 있는 **`run_summary.bat`** 파일을 더블 클릭하세요.

### 터미널 사용자
```bash
python main.py
```

### 실행 과정
1.  프로그램이 시작되면 로고와 함께 준비 상태가 됩니다.
2.  **"어떻게 요약해드릴까요?"** 라고 묻습니다. 자유롭게 명령하세요.
    *   *"최근 1주일간 작성된 일기만 모아서 감정 변화를 분석해줘"*
    *   *"아이디어 노트에서 사업 아이템만 뽑아서 리스트로 정리해줘"*
3.  **"제목은 무엇으로 할까요?"** 라고 묻습니다. 결과 보고서의 제목을 정해주세요.
    *   (그냥 엔터 치면 'AI Report'로 저장됩니다.)
4.  잠시 기다리면... **Notion에 요약 페이지가 짠! 하고 생성됩니다.** 🎉

---

## 📦 파일 구조 (File Structure)

*   `main.py`: 프로그램의 **메인 실행 파일**입니다. 사용자 입력을 받고 전체 흐름을 제어합니다.
*   `notion_connector.py`: Notion API와 통신하며 데이터를 가져오고 페이지를 생성합니다. (재귀적 탐색 로직 포함)
*   `summarizer.py`: Google Gemini API를 사용하여 텍스트를 요약합니다. (모델 Fallback 로직 포함)
*   `requirements.txt`: 필요한 파이썬 라이브러리 목록입니다.

---

## ⚠️ 주의사항

*   **보안**: `.env` 파일에는 개인적인 API 키가 들어있으므로, **절대 GitHub에 업로드하지 마세요!** (이미 `.gitignore`에 설정되어 있습니다.)
*   **할당량**: Gemini API 무료 티어는 분당 요청 제한이 있을 수 있습니다. 프로그램에 속도 조절 로직이 포함되어 있으나, 너무 많은 요청을 보내면 일시적으로 멈출 수 있습니다.

---

Made with ❤️ by Notion & AI Enthusiasts
