@echo off
setlocal EnableExtensions
cd /d c:\dev\AI_indkøbsseddel
if not exist .venv\Scripts\activate.bat (
    echo Virtuelt miljoe blev ikke fundet.
    echo Kor install.bat forst.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo.
echo Starter Lokalt Indkob...
echo Abn din browser paa http://localhost:8501
echo.

python -m streamlit run app.py
pause
endlocal