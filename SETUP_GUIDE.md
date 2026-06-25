# DiVeL (Digital Evidence Locker) - Complete Setup & Troubleshooting Guide

## 🎯 Quick Start (After Fixes Applied)

### 1. Backend Startup

```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8046
```

**On startup, you should see:**
```
Connected to DynamoDB Tables: forensichain-cases, forensichain-metadata
Blockchain Connected: 0x5FbDB2315678afecb367f032d93F642f64180aa3
DATABASE EMPTY - SEEDING WITH INITIAL DATA
✅ Database seeding completed on startup
INFO:     Uvicorn running on http://0.0.0.0:8046 (Press CTRL+C to quit)
```

### 2. Frontend Startup

```bash
cd frontend
npm run dev
```

Visit: `http://localhost:5173`

### 3. Access Swagger API Documentation

Visit: `http://localhost:8046/docs` to explore all endpoints.

---

## 🔧 What Was Fixed

### Problem #1: Empty Database ✅ FIXED
**Issue**: DynamoDB table was connected but contained no data  
**Solution**: Added auto-seeding on backend startup in `main.py`

### Problem #2: Type Mismatches ✅ FIXED
**Issue**: Latitude/Longitude stored as strings, frontend expected numbers  
**Solution**: Updated `app/models/case.py` to use `float` type with validation

### Problem #3: Insufficient Error Handling ✅ FIXED
**Issue**: Frontend showed no error messages or retry logic  
**Solution**: Enhanced `Dashboard.tsx` with error UI, retry mechanism, and better logging

### Problem #4: API URL Configuration ✅ FIXED
**Issue**: Hardcoded port might not match actual backend port  
**Solution**: Implemented fallback URL detection in `frontend/src/services/api.ts`

### Problem #5: Missing Type Safety ✅ FIXED
**Issue**: No TypeScript types for Case objects  
**Solution**: Created comprehensive types in `frontend/src/types/case.ts`

---

## 📋 Files Modified

### Backend
- `backend/main.py` - Added auto-seeding on startup and CORS configuration
- `backend/app/models/case.py` - Fixed latitude/longitude types (string → float)
- `backend/app/api/cases.py` - Enhanced with error handling and type conversion
- `backend/app/api/init.py` - NEW - Manual seed and health check endpoints

### Frontend
- `frontend/src/pages/Dashboard.tsx` - Enhanced error handling and loading states
- `frontend/src/services/api.ts` - Added proper types and error interceptors
- `frontend/src/types/case.ts` - NEW - Complete TypeScript type definitions

---

## 🧪 Testing the Fix

### Test 1: Check Database Seeding
```bash
curl http://localhost:8046/api/init/status
```

**Expected Response:**
```json
{
  "initialized": true,
  "cases_count": 2,
  "mode": "DynamoDB",
  "status": "ready"
}
```

### Test 2: Fetch Cases via API
```bash
curl http://localhost:8046/api/cases
```

**Expected Response:**
```json
{
  "cases": [
    {
      "id": "...",
      "caseNumber": "CR-ORG-2025-...",
      "district": "International Crime Unit",
      "status": "Under Investigation",
      "latitude": 46.2044,
      "longitude": 6.1432,
      ...
    }
  ]
}
```

### Test 3: Check Frontend Dashboard
1. Open `http://localhost:5173`
2. Navigate to "Cases" section
3. Should see 2 cases displayed (Operation Red Ledger, Project Titan)

---

## 🚨 Troubleshooting

### Issue: Backend won't start - "ModuleNotFoundError: pydantic_settings"
**Solution:**
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8046
```

### Issue: Port 8046 already in use
**Solution:**
```bash
# On Windows
netstat -ano | findstr :8046
taskkill /PID <PID> /F

# On Mac/Linux
lsof -i :8046
kill -9 <PID>
```

### Issue: "ERROR: [Errno 10048] only one usage of each socket address"
**Solution:** Another process is using the port. Kill it first, then restart backend.

### Issue: Cases not appearing after fix
**Steps to diagnose:**
1. Check backend logs for "DATABASE EMPTY - SEEDING"
2. Verify DynamoDB connection: `curl http://localhost:8046/api/init/status`
3. Check browser console (F12) for API errors
4. Manually seed: `curl -X POST http://localhost:8046/api/init/seed`

### Issue: CORS Error in Frontend
**Solution:** The backend now has expanded CORS settings. If still failing:
```python
# In backend/main.py, add your URL to origins list:
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "YOUR_URL_HERE",  # Add your URL
]
```

### Issue: "Cannot GET /api/cases" - 404 Error
**Solution:** API routes must be registered in `main.py`. Verify the init router was added.

### Issue: Cases show 0 latitude/longitude
**Solution:** These are now validated and converted to floats. If still seeing 0:
```python
# Check database.py list_cases() function
# Ensure it returns floats for lat/long
```

---

## 🔄 Manual Database Operations

### View Database Status
```bash
curl http://localhost:8046/api/init/status
```

### Manually Seed Database
```bash
curl -X POST http://localhost:8046/api/init/seed
```

### Clear Database (Use Caution!)
```bash
curl -X POST http://localhost:8046/api/init/clear
```

### Check Health
```bash
curl http://localhost:8046/api/init/health
```

---

## 📊 Expected API Responses

### GET /api/cases
Returns all cases with proper structure:
```json
{
  "cases": [
    {
      "id": "uuid",
      "caseNumber": "CR-ORG-2025-XXXX",
      "district": "String",
      "unit": "String",
      "status": "Under Investigation | Pending Trial | Closed | Convicted | ...",
      "lawSections": ["PMLA Act", "IPC 120B"],
      "dateOfOffence": "2026-03-26",
      "dateOfReport": "2026-03-31",
      "sceneOfCrime": "Multiple Locations",
      "latitude": 46.2044,
      "longitude": 6.1432,
      "accused": [
        {
          "id": "uuid",
          "name": "Name",
          "status": "Wanted | Arrested",
          "gender": "Male | Female",
          "age": "55"
        }
      ],
      "evidence": [
        {
          "id": "uuid",
          "name": "Evidence Name",
          "type": "document | audio | image | video",
          "uploadedAt": "2026-06-24T21:04:24",
          "metadata": {...}
        }
      ],
      "createdAt": "2026-06-24T21:04:24",
      "updatedAt": "2026-06-24T21:04:24",
      "hash": "SHA256_HASH",
      "tx_hash": "BLOCKCHAIN_TX_HASH"
    }
  ]
}
```

### GET /api/init/status
```json
{
  "initialized": true,
  "cases_count": 2,
  "mode": "DynamoDB",
  "status": "ready"
}
```

---

## 🔐 Authentication & Verification

### Blockchain Verification
Each case has:
- `hash`: SHA-256 hash of case data
- `tx_hash`: Blockchain transaction hash for verification

### Evidence Verification
Each evidence item includes:
- `metadata.tx_hash`: Blockchain transaction ID
- `metadata.uploader_role`: Who uploaded the evidence
- `metadata.content_type`: File MIME type

---

## 📱 Frontend Components Status

| Component | Status | Notes |
|-----------|--------|-------|
| Dashboard | ✅ Fixed | Now shows cases, error handling added |
| CaseCard | ✅ Works | Properly displays case data |
| CaseFilters | ✅ Works | Filters work with data |
| CaseUploadModal | ✅ Works | Can create new cases |
| API Service | ✅ Enhanced | Proper typing and error handling |
| Types | ✅ Created | Full TypeScript support |

---

## 🚀 Production Deployment

### Before Going Live:
1. ✅ Test with actual DynamoDB credentials
2. ✅ Verify AWS IAM permissions for tables
3. ✅ Update CORS origins for your domain
4. ✅ Configure environment variables (.env)
5. ✅ Test blockchain connectivity
6. ✅ Set up monitoring for database errors
7. ✅ Implement rate limiting
8. ✅ Add API authentication/validation

### Environment Variables (.env)
```
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=eu-north-1
DYNAMODB_TABLE_CASES=forensichain-cases
DYNAMODB_TABLE_EVIDENCE=forensichain-metadata
BLOCKCHAIN_RPC_URL=http://localhost:8545
```

---

## 📞 Support

If cases still don't appear:
1. Check backend logs for errors
2. Verify database connection: `curl http://localhost:8046/api/init/status`
3. Check browser console (F12) for frontend errors
4. Try manual seed: `curl -X POST http://localhost:8046/api/init/seed`
5. Review the complete logs with timestamps

---

## ✅ Success Checklist

- [ ] Backend starts without errors
- [ ] "DATABASE SEEDING" message appears on startup
- [ ] `http://localhost:8046/api/init/status` returns `cases_count > 0`
- [ ] Frontend loads at `http://localhost:5173`
- [ ] Cases appear on dashboard
- [ ] Case cards show case number, district, status
- [ ] Clicking case opens details
- [ ] Filters work correctly
- [ ] No errors in browser console (F12)
- [ ] No errors in backend logs

If all checkboxes pass, the system is working correctly! 🎉
