@echo off
cd /d "%~dp0"
python -u run_project.py %*
if errorlevel 1 echo Pipeline stopped with an error. Read the message above.
pause

