# Voice AI Server - Quick Start Guide

## 🚀 Starting the Server

### Option 1: Using the Management Script (Recommended)
```bash
cd backend
.\server.bat
```
Then select option `[1] Start Server`

### Option 2: Direct Command
```bash
cd backend
.\venv\Scripts\python.exe run.py
```

---

## 🛑 Stopping the Server

### Option 1: Using the Management Script
```bash
.\server.bat
```
Then select option `[2] Stop Server`

### Option 2: Manual Command
```powershell
# Find the process
netstat -ano | findstr :8000

# Kill it (replace PID with actual process ID)
taskkill /F /PID <PID>
```

### Option 3: If server is in same terminal
Press `CTRL+C`

---

## 🔄 Common Issues

### ❌ Error: "Port 8000 already in use"
**Problem:** Another instance is already running

**Solution:**
```bash
# Stop all instances on port 8000
for /f "tokens=5" %a in ('netstat -ano ^| findstr :8000') do taskkill /F /PID %a
```

Or use the server.bat script: `.\server.bat` → Option `[2] Stop Server`

---

## ✅ Verify Server is Running

### Check Status:
```bash
# Using server.bat
.\server.bat
# Option [4] Check Server Status

# Or manually
netstat -ano | findstr :8000
```

### Test API:
```bash
curl http://localhost:8000/calls
```

**Expected:** JSON response with call history (may be empty array `[]`)

---

## 📝 Server Logs

**Location:** `backend/logs/debug.log`

**View in real-time:**
```powershell
Get-Content .\logs\debug.log -Wait -Tail 50
```

---

## 🔧 Environment Setup

**Before first run, ensure:**
1. MongoDB is running locally
2. `.env` file is configured with API keys
3. Virtual environment is activated (done automatically by scripts)

---

## 📊 Monitoring

**While server is running, you can monitor:**
- Logs: `backend/logs/debug.log`
- ChromaDB: `backend/data/chroma/`
- MongoDB: Use MongoDB Compass on `mongodb://localhost:27017`

---

## 🎯 Quick Commands Reference

| Action | Command |
|--------|---------|
| Start | `.\venv\Scripts\python.exe run.py` |
| Stop | `taskkill /F /PID <PID>` |
| Status | `netstat -ano \| findstr :8000` |
| Test | `curl http://localhost:8000/calls` |
| Logs | `Get-Content .\logs\debug.log -Wait` |

---

## 💡 Pro Tips

1. **Always use server.bat** for easy management
2. **Check logs** if something isn't working: `logs/debug.log`
3. **Stop properly** before restarting to avoid port conflicts
4. **MongoDB must be running** locally for the server to start

---

**Server URL:** `http://localhost:8000`
**API Docs:** `http://localhost:8000/docs` (FastAPI auto-generated)

**Ready to start! Run `.\server.bat` and select option 1** 🚀
