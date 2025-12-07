@echo off
echo Starting Vasudeva...

echo Starting backend server...
start cmd /k "cd backend && venv\Scripts\activate && python api.py"

timeout /t 3 /nobreak >nul

echo Starting frontend server...
start cmd /k "cd frontend && npm run dev"

echo.
echo Vasudeva is starting!
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Close the command windows to stop the servers.


