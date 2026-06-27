from fastapi import APIRouter, HTTPException, status
from app.services.database import db
from app.models.case import CaseCreate, Case, Accused, Evidence
import uuid
import json
from datetime import datetime
from app.services.blockchain import blockchain

router = APIRouter()

# Valid case statuses
CASE_STATUSES = [
    "Under Investigation",
    "Pending Trial",
    "Closed",
    "Convicted",
    "Charge Sheet Filed",
    "Arrested",
    "Bail Granted",
    "Acquitted"
]

@router.get("")
@router.get("/")
def get_cases():
    """Retrieve all cases from database"""
    try:
        cases = db.list_cases()
        
        # Ensure proper data types for numeric fields
        for case in cases:
            try:
                if isinstance(case.get('latitude'), str):
                    case['latitude'] = float(case['latitude'])
                if isinstance(case.get('longitude'), str):
                    case['longitude'] = float(case['longitude'])
            except (ValueError, TypeError):
                case['latitude'] = 0.0
                case['longitude'] = 0.0
        
        return {"cases": cases}
    except Exception as e:
        print(f"Error fetching cases: {e}")
        return {"cases": [], "error": str(e)}

@router.get("/{case_id}/knowledge-graph")
def get_case_knowledge_graph(case_id: str):
    """Build a consolidated knowledge graph for the requested case."""
    try:
        case = db.get_case(case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        evidence_items = case.get("evidence") or db.list_case_evidence(case_id)
        nodes_map = {}
        links = []

        # Add the primary case node
        case_node_id = f"case-{case.get('id')}"
        nodes_map[case_node_id] = {
            "id": case_node_id,
            "label": case.get("caseNumber", "Case"),
            "group": "Case",
            "type": "case",
        }

        # Add evidence and entity nodes
        for evidence in evidence_items or []:
            evidence_id = evidence.get("evidence_id") or evidence.get("id") or evidence.get("filename") or evidence.get("name")
            evidence_label = evidence.get("filename") or evidence.get("name") or evidence_id
            evidence_node_id = f"evidence-{evidence_id}"

            if evidence_node_id not in nodes_map:
                nodes_map[evidence_node_id] = {
                    "id": evidence_node_id,
                    "label": evidence_label,
                    "group": "Evidence",
                    "type": "evidence",
                    "evidence_id": evidence_id,
                }

            links.append({
                "source": case_node_id,
                "target": evidence_node_id,
                "label": "contains",
            })

            kg = evidence.get("metadata", {}).get("knowledge_graph") or evidence.get("knowledge_graph")
            if not kg:
                continue

            for node in kg.get("nodes", []) or []:
                node_id = node.get("id")
                if not node_id:
                    continue
                if node_id not in nodes_map:
                    nodes_map[node_id] = {
                        "id": node_id,
                        "label": node_id,
                        "group": node.get("group", "Entity"),
                        "type": node.get("group", "entity").toLowerCase(),
                    }

            for link in kg.get("links", []) or []:
                source = link.get("source")
                target = link.get("target")
                if source and target:
                    links.append({
                        "source": source,
                        "target": target,
                        "label": link.get("value") or link.get("relationship") or "related",
                        "evidence_id": evidence_id,
                    })

                    # Ensure source/target nodes exist
                    if source not in nodes_map:
                        nodes_map[source] = {"id": source, "label": source, "group": "Entity", "type": "entity"}
                    if target not in nodes_map:
                        nodes_map[target] = {"id": target, "label": target, "group": "Entity", "type": "entity"}

        graph = {
            "case_id": case_id,
            "case_number": case.get("caseNumber"),
            "nodes": list(nodes_map.values()),
            "links": links,
            "summary": case.get("aiSummary") or "",
            "evidence_count": len(evidence_items or []),
            "node_count": len(nodes_map),
            "link_count": len(links),
        }
        return graph
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error building case knowledge graph {case_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{case_id}")
def get_case(case_id: str):
    """Retrieve a specific case by ID"""
    try:
        case = db.get_case(case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Ensure proper data types
        try:
            if isinstance(case.get('latitude'), str):
                case['latitude'] = float(case['latitude'])
            if isinstance(case.get('longitude'), str):
                case['longitude'] = float(case['longitude'])
        except (ValueError, TypeError):
            case['latitude'] = 0.0
            case['longitude'] = 0.0
        
        return {"case": case}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching case {case_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
@router.post("/")
def create_case(case_in: CaseCreate):
    """Create a new case and store on blockchain"""
    try:
        case_data = case_in.dict()
        case_data["id"] = str(uuid.uuid4())
        case_data["caseNumber"] = f"CR-ORG-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"
        case_data["status"] = "Under Investigation"
        case_data["createdAt"] = str(datetime.now())
        case_data["updatedAt"] = str(datetime.now())
        case_data["evidence"] = []
        
        # Ensure numeric fields are floats
        case_data["latitude"] = float(case_data.get("latitude", 0.0))
        case_data["longitude"] = float(case_data.get("longitude", 0.0))
        
        # Hash the case metadata
        case_str = json.dumps(case_data, sort_keys=True, default=str).encode('utf-8')
        case_hash = blockchain.calculate_hash(case_str)
        
        print(f"\n{'='*60}")
        print(f"CASE UPLOADED SUCCESSFULLY!")
        print(f"Case ID: {case_data['id']}")
        print(f"Case Number: {case_data['caseNumber']}")
        print(f"Generated SHA-256 Hash: {case_hash}")
        print(f"{'='*60}\n")
        
        # Store on blockchain
        blockchain_record = blockchain.store_hash_on_chain(
            case_id=case_data["id"],
            evidence_id=f"CASE_META_{case_data['id']}",
            file_hash=case_hash,
            file_type="Application/JSON (Case Metadata)",
            uploader_role="System",
            previous_hash=""
        )

        case_data["hash"] = case_hash
        case_data["tx_hash"] = blockchain_record.get("tx_hash")
        case_data["blockchain"] = blockchain_record
        
        db.create_case(case_data)
        return case_data
    except Exception as e:
        print(f"Error creating case: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{case_id}")
def update_case(case_id: str, case_update: dict):
    """Update an existing case"""
    try:
        existing_case = db.get_case(case_id)
        if not existing_case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Update fields
        existing_case.update(case_update)
        existing_case["updatedAt"] = str(datetime.now())
        
        # Ensure numeric fields
        existing_case["latitude"] = float(existing_case.get("latitude", 0.0))
        existing_case["longitude"] = float(existing_case.get("longitude", 0.0))
        
        db.create_case(existing_case)  # Update in DB
        return {"case": existing_case}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating case: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{case_id}")
def delete_case(case_id: str):
    """Delete a case (soft delete - mark as archived)"""
    try:
        case = db.get_case(case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        case["status"] = "Archived"
        case["updatedAt"] = str(datetime.now())
        db.create_case(case)  # Update status
        return {"message": "Case archived successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting case: {e}")
        raise HTTPException(status_code=500, detail=str(e))
