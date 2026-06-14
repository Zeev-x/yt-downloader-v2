@echo off
python -m venv rey
call rey\Scripts\activate.bat
pip install -r requirements.txt
echo Instalation complete.
pause