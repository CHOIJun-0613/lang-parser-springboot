cd .. 
call .venv\Scripts\activate
cmd /c "python -m csa.cli.main analyze --all-objects --clean"
cd commands
echo [현재 디렉토리] : %cd%
pause