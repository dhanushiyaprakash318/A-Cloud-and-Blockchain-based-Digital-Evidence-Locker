from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import cases, evidence, auth
import os
import sys

# Fix Windows console encoding to support Unicode output
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

app = FastAPI(title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json")

# CORS
origins = [
    "http://localhost:5173",  # Vite default
    "http://localhost:5174",  # Vite alternate
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:8046",
    "http://0.0.0.0:5173",
    "http://0.0.0.0:5174",
    "http://0.0.0.0:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(evidence.router, prefix=f"{settings.API_V1_STR}/evidence", tags=["evidence"])
app.include_router(cases.router, prefix=f"{settings.API_V1_STR}/cases", tags=["cases"])
from app.api import init as init_router
app.include_router(init_router.router, prefix=f"{settings.API_V1_STR}/init", tags=["initialization"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Digital Evidence Locker API"}

@app.on_event("startup")
async def startup_event():
    """Initialize database with seed data if empty"""
    from app.services.database import db
    
    try:
        cases_list = db.list_cases()
        
        if not cases_list or len(cases_list) == 0:
            print("\n" + "="*60)
            print("DATABASE EMPTY - SEEDING WITH INITIAL DATA")
            print("="*60)
            
            # Run seed script
            seed_script_path = os.path.join(os.path.dirname(__file__), "seed_complex_cases.py")
            if os.path.exists(seed_script_path):
                # Import and run the seed
                sys.path.insert(0, os.path.dirname(__file__))
                import seed_complex_cases
                seed_complex_cases.run()
                print("[OK] Database seeding completed on startup")
            else:
                print("[WARN] Seed script not found, skipping initial data load")
        else:
            print(f"\n[OK] Database ready with {len(cases_list)} cases")
    except Exception as e:
        print(f"[WARN] Error during startup initialization: {e}")

# Reload triggered to load Hardhat configuration
