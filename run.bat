@echo off
cls
echo ----------------------------
echo Running Flask Project Setup
echo ----------------------------

REM Step 1: Install requirements if file exists
if exist requirements.txt (
    echo Installing requirements...
    %PIP_CMD% install -r requirements.txt
) else (
    echo No requirements.txt found, skipping install.
)

REM Step 2: Try running the app
echo Starting Flask app...

py app.py
if %errorlevel% neq 0 (
    echo py failed, trying python...
    python app.py
)

REM Step 3: Open VS Code
echo Opening Visual Studio Code...
code .
