@echo off
REM ===== BatiPlan Studio : build the Windows installer (run on a Windows PC with Python 3.12 and Inno Setup 6) =====
REM 1) Edit batiplan\brand.py (company, e-mail, WhatsApp, website)  2) tools\make_keys.py must have been run ONCE (never again)
py -3 -m venv .venv || goto :err
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller || goto :err
python tests\test_all.py || goto :err
pyinstaller --noconfirm --clean batiplan.spec || goto :err
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" installer.iss) else echo Inno Setup not found: install it, then run ISCC installer.iss
echo.
echo DONE -> Output\BatiPlanStudio_Setup.exe   (sign it with your code-signing certificate before selling)
goto :eof
:err
echo BUILD FAILED
exit /b 1
