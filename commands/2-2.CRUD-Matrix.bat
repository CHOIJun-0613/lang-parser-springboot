cd .. 
call .venv\Scripts\activate
cmd /c "python -m csa.cli.main crud-matrix --project-name car-center-devlab --output-format excel"
cd commands
echo [현재 디렉토리] : %cd%
pause