@echo off
setlocal
chcp 65001 > NUL

echo 📦 Notion AI Summarizer Setup...
echo.

:: 1. 파이썬 확인
python --version > NUL 2>&1
if %errorlevel% neq 0 goto :NO_PYTHON

:: 2. 가상환경 확인
if not exist "venv" goto :CREATE_VENV

:CHECK_VENV
echo [1/3] 가상환경(venv) 확인 중...
".\venv\Scripts\python.exe" -c "print('OK')" > NUL 2>&1
if %errorlevel% neq 0 goto :REPAIR_VENV
echo  ✅ 가상환경이 정상입니다.
goto :INSTALL_DEPS

:REPAIR_VENV
echo [WARNING] 가상환경 손상 감지! (폴더 이동 등)
echo 🧹 자동으로 복구합니다...
rmdir /s /q venv
goto :CREATE_VENV

:CREATE_VENV
echo [1/3] 새 가상환경(venv) 생성 중...
python -m venv venv
if %errorlevel% neq 0 goto :VENV_FAIL
goto :INSTALL_DEPS

:INSTALL_DEPS
echo [2/3] 라이브러리 설치 중...
".\venv\Scripts\pip.exe" install -r requirements.txt
if %errorlevel% neq 0 goto :PIP_FAIL

echo.
echo [3/3] 설정 완료! 🎉
echo 이제 'run_summary.bat'을 실행하세요.
goto :END

:NO_PYTHON
echo [ERROR] Python이 설치되어 있지 않습니다.
echo https://www.python.org/ 에서 설치해주세요.
goto :END

:VENV_FAIL
echo [ERROR] 가상환경 생성에 실패했습니다.
goto :END

:PIP_FAIL
echo [ERROR] 패키지 설치에 실패했습니다.
goto :END

:END
echo.
pause
