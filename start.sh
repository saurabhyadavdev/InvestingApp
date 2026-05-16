#!/bin/bash
# InvestIQ launcher — starts backend + frontend and opens the browser.

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_LOG="$PROJECT_DIR/backend.log"
FRONTEND_LOG="$PROJECT_DIR/frontend.log"
BACKEND_PORT=8000
FRONTEND_PORT=3000

cd "$PROJECT_DIR"

# ── Kill any existing processes on the ports ────────────────────────────────
kill_port() {
  local pid
  pid=$(lsof -ti :"$1" 2>/dev/null || true)
  if [ -n "$pid" ]; then
    echo "Stopping existing process on port $1 (PID $pid)..."
    kill "$pid" 2>/dev/null || true
    sleep 1
  fi
}

kill_port $BACKEND_PORT
kill_port $FRONTEND_PORT

# ── Backend ──────────────────────────────────────────────────────────────────
echo "Starting backend on port $BACKEND_PORT..."
python3 -m uvicorn backend.main:app --port $BACKEND_PORT > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

# Wait for backend to be ready (up to 30 s)
echo -n "Waiting for backend"
for i in $(seq 1 30); do
  if curl -sf "http://localhost:$BACKEND_PORT/health" > /dev/null 2>&1; then
    echo " ready."
    break
  fi
  echo -n "."
  sleep 1
done

# ── Frontend ─────────────────────────────────────────────────────────────────
echo "Starting frontend on port $FRONTEND_PORT..."
cd "$PROJECT_DIR/frontend"
npm run dev > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

# Wait for Vite to be ready (up to 20 s)
echo -n "Waiting for frontend"
for i in $(seq 1 20); do
  if curl -sf "http://localhost:$FRONTEND_PORT" > /dev/null 2>&1; then
    echo " ready."
    break
  fi
  echo -n "."
  sleep 1
done

# ── Open browser ──────────────────────────────────────────────────────────────
echo "Opening http://localhost:$FRONTEND_PORT ..."
open "http://localhost:$FRONTEND_PORT"

echo ""
echo "InvestIQ is running."
echo "  Backend log : $BACKEND_LOG"
echo "  Frontend log: $FRONTEND_LOG"
echo ""
echo "Press Ctrl+C to stop both servers."

# ── Wait and clean up on Ctrl+C ───────────────────────────────────────────────
trap "echo ''; echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait
