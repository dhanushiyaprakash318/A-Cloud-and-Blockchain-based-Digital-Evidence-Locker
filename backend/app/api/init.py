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
            "mode": "DynamoDB" if db.cases_table else "Unavailable"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }, 500

@router.post("/seed")
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

@router.post("/clear")
def clear_database():
    """
    Clear all data from database (for testing/reset)
    WARNING: This is destructive!
    """
    try:
        # Clear DynamoDB if active
        if db.cases_table or db.evidence_table:
            if db.cases_table:
                response = db.cases_table.scan()
                for item in response.get('Items', []):
                    db.cases_table.delete_item(Key={'id': item['id']})
            if db.evidence_table:
                response = db.evidence_table.scan()
                for item in response.get('Items', []):
                    db.evidence_table.delete_item(Key={'evidence_id': item['evidence_id']})
            print("[Init API] Cleared DynamoDB tables.")

        return {
            "message": "Database cleared successfully",
            "status": "cleared"
        }
    except Exception as e:
        print(f"Error clearing database: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
def init_status():
    """Get current database initialization status"""
    try:
        cases = db.list_cases()
        mode = "DynamoDB" if db.cases_table else "Unavailable"
        
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


@router.get("/env")
def init_env():
    """Return masked environment diagnostic info for troubleshooting (no secrets leaked)."""
    def mask(val):
        if not val:
            return None
        s = str(val)
        if len(s) <= 8:
            return s[0] + "*****"
        return s[:4] + "******" + s[-4:]

    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID") or None
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY") or None
    aws_session = os.getenv("AWS_SESSION_TOKEN") or None
    private_key_present = bool(os.getenv("PRIVATE_KEY") or os.getenv("BLOCKCHAIN_PRIVATE_KEY"))

    return {
        "aws_access_key_id_masked": mask(aws_access_key),
        "aws_secret_access_key_present": bool(aws_secret),
        "aws_session_token_present": bool(aws_session),
        "private_key_present": private_key_present,
        "dynamodb_tables_configured": bool(db.cases_table and db.evidence_table),
        "dynamodb_mode": "DynamoDB" if db.cases_table else "Local"
    }
