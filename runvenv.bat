@echo off
REM This batch file activates the Python virtual environment in the .venv directory.

echo Activating virtual environment...

REM Check if the activation script exists
IF NOT EXIST .\.venv\Scripts\activate.bat (
    echo Error: The virtual environment activation script was not found at .\.venv\Scripts\activate.bat
    echo Please ensure the virtual environment has been created in the '.venv' directory.
    pause
    exit /b 1
)

REM Activate the virtual environment
call .\.venv\Scripts\activate.bat

echo Virtual environment activated. The command prompt is now using the virtual environment's Python interpreter.

REM Keeps the command prompt open after activation
cmd /k