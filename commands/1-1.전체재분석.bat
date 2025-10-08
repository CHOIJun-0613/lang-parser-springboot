cd .. 
call .venv\Scripts\activate
cmd /c "python -m csa.cli.main analyze --all-objects --clean"