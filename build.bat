@echo off
REM Build Anees for Windows
echo Building Anees for Windows...
.venv\Scripts\pyinstaller anees.spec --clean --noconfirm
echo Done: dist\Anees\Anees.exe
