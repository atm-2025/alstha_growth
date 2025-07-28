@echo off
cd /d "%~dp0"

set REMOTE_URL=https://github.com/atm-2025/alstha_growth
set BRANCH=main

REM ==== INIT IF NEEDED ====
if not exist ".git" (
    echo [INFO] Git not initialized. Initializing...
    git init
    git remote add origin %REMOTE_URL%
    git branch -M %BRANCH%
)

REM ==== ADD ONLY EXISTING FILES ====
powershell -Command "Get-ChildItem -Recurse -File | ForEach-Object { git add $_.FullName }"

REM ==== COMMIT IF NEEDED ====
git diff --cached --quiet
IF %ERRORLEVEL%==0 (
    echo [INFO] Nothing to commit.
    pause
    exit /b
)

for /f %%i in ('powershell -command "Get-Date -Format yyyy-MM-dd_HH-mm-ss"') do set timestamp=%%i
git commit -m "Auto commit %timestamp%"

git push -u origin %BRANCH%

echo [SUCCESS] Only added/updated files pushed. Deletions ignored.
pause
