#!/bin/bash

echo "🕉️  Starting Vasudeva..."

# Check if backend is already running
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "✅ Backend already running on port 8000"
else
    echo "🚀 Starting backend server..."
    cd backend
    source venv/bin/activate 2>/dev/null || echo "⚠️  Virtual environment not activated"
    python api.py &
    BACKEND_PID=$!
    cd ..
    sleep 3
    echo "✅ Backend started (PID: $BACKEND_PID)"
fi

# Check if frontend is already running
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null ; then
    echo "✅ Frontend already running on port 3000"
else
    echo "🚀 Starting frontend server..."
    cd frontend
    npm run dev &
    FRONTEND_PID=$!
    cd ..
    sleep 2
    echo "✅ Frontend started (PID: $FRONTEND_PID)"
fi

echo ""
echo "✨ Vasudeva is ready!"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all servers"

# Keep script running
wait

