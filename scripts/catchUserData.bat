@echo off
python "%~dp0capture_session.py" %*
if "%CI%"=="" if "%JENKINS_URL%"=="" pause
