"""
Database initialization and health check endpoints
Provides manual seeding and status monitoring
"""
from fastapi import APIRouter, HTTPException
from app.services.database import db
import sys
import os

router = APIRouter()

@router.get("/health")
def health_check():
    """Health check endpoint - verifies database connectivity"""
    try:
        cases = db.list_cases()
        return {
            "status": "healthy",
            "database": "connected",
            "cases_count": len(cases),
            "mode": "DynamoDB" if db.cases_table else "Local (local_db.json)"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }, 500

@router.post("/init/seed")
def seed_database():
    """
    Manually trigger database seeding
    Populates the database with sample case data if empty
    """
    try:
        # Check current state
        existing_cases = db.list_cases()
        
        if existing_cases and len(existing_cases) > 0:
            return {
                "message": "Database already contains data",
                "cases_count": len(existing_cases),
                "action": "skipped"
            }
        
        print("\n" + "="*60)
        print("MANUAL SEED INITIATED")
        print("="*60)
        
        # Run the seed script
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        import seed_complex_cases
        seed_complex_cases.run()
        
        # Verify seeding worked
        new_cases = db.list_cases()
        
        return {
            "message": "Database seeding completed successfully",
            "cases_loaded": len(new_cases),
            "status": "success"
        }
    except Exception as e:
        print(f"Error during seeding: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/init/clear")
def clear_database():
    """
    Clear all data from database (for testing/reset)
    WARNING: This is destructive!
    """
    try:
        if hasattr(db, '_write_local_db'):
            # Local mode
            db._write_local_db({"cases": [], "evidence": []})
        elif hasattr(db, 'cases_table'):
            # DynamoDB mode - scan and delete all items
            if db.cases_table:
                response = db.cases_table.scan()
                for item in response.get('Items', []):
                    db.cases_table.delete_item(Key={'id': item['id']})
        
        return {
            "message": "Database cleared successfully",
            "status": "cleared"
        }
    except Exception as e:
        print(f"Error clearing database: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/init/status")
def init_status():
    """Get current database initialization status"""
    try:
        cases = db.list_cases()
        mode = "DynamoDB" if db.cases_table else "Local (local_db.json)"
        
        return {
            "initialized": len(cases) > 0,
            "cases_count": len(cases),
            "mode": mode,
            "status": "ready" if len(cases) > 0 else "empty"
        }
    except Exception as e:
        return {
            "initialized": False,
            "error": str(e),
            "status": "error"
        }, 500
