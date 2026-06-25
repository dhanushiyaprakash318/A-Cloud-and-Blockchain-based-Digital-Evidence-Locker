import sys
import os
import boto3
import uuid
import json
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

# --- Local DB Fallback Utility ---
class LocalTable:
    def __init__(self, table_type: str, db_path: str = "local_db.json"):
        self.table_type = table_type # 'cases' or 'evidence'
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_path)
        self._ensure_db()

    def _ensure_db(self):
        if not os.path.exists(self.db_path):
            with open(self.db_path, 'w') as f:
                json.dump({"cases": [], "evidence": []}, f)

    def _read_db(self):
        with open(self.db_path, 'r') as f:
            return json.load(f)

    def _write_db(self, data):
        with open(self.db_path, 'w') as f:
            json.dump(data, f, indent=4)

    def put_item(self, Item: Dict[str, Any]):
        data = self._read_db()
        key = 'id' if self.table_type == 'cases' else 'evidence_id'
        
        # Remove existing with same ID (simple update)
        # Handle case where list is dict (legacy/bug compat)
        target_list = data.get(self.table_type, [])
        target_list = data.get(self.table_type, [])
        if isinstance(target_list, dict):
            # Detect legacy/incompatible dict format and reset to list
            print(f"Warning: '{self.table_type}' is a dict, resetting to list for compatibility.")
            target_list = []
            data[self.table_type] = target_list
        
        target_list = [i for i in target_list if i.get(key) != Item.get(key)]
        
        target_list.append(Item)
        data[self.table_type] = target_list
        self._write_db(data)

def get_tables():
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        try:
            dynamodb = boto3.resource(
                'dynamodb',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            # Test connection
            dynamodb.Table(settings.DYNAMODB_TABLE_CASES).load()
            
            cases_table = dynamodb.Table(settings.DYNAMODB_TABLE_CASES)
            evidence_table = dynamodb.Table(settings.DYNAMODB_TABLE_EVIDENCE)
            print("Using DynamoDB tables.")
            return cases_table, evidence_table
        except Exception as e:
            print(f"Error connecting to DynamoDB: {e}. Falling back to local_db.json")
    else:
        print("No AWS Credentials. Falling back to local_db.json")
    
    cases_table = LocalTable("cases")
    evidence_table = LocalTable("evidence")
    return cases_table, evidence_table

def run():
    print("🚀 Starting Seed Script...")
    cases_table, evidence_table = get_tables()

    # --- CASE 1: Operation Red Ledger ---
    print("🚀 Adding COMPLEX Case 1: Operation Red Ledger...")
    case_id_1 = str(uuid.uuid4())
    case_number_1 = f"CR-ORG-2025-{random.randint(1000, 9999)}"
    
    description_1 = "Operation 'Red Ledger': Multi-national money laundering syndicate using crypto-currency to funnel proceeds from illegal arms trade. The syndicate operates through a network of shell companies in Panama and Singapore."
    
    evidence_items_1 = [
        {
            "filename": "forensic_hdd_report.pdf",
            "type": "document",
            "summary": "Forensic analysis of the seized server HDD (Serial: WD-X99) reveals 10,000+ encrypted chat logs. Decryption of 'Partition A' uncovered communications between 'Kingpin' and 'Supplier_Alpha' regarding shipment of 'Hardware_X' to Port 4. Keys found in local wallet.dat.",
            "entities": [
                {"name": "Kingpin", "type": "Person"},
                {"name": "Supplier_Alpha", "type": "Person"},
                {"name": "HDD WD-X99", "type": "Evidence"},
                {"name": "Port 4", "type": "Location"}
            ],
            "links": [
                {"source": "HDD WD-X99", "target": "Kingpin", "value": "Contains chats of"},
                {"source": "Kingpin", "target": "Supplier_Alpha", "value": "Discussed shipment"},
                {"source": "Supplier_Alpha", "target": "Port 4", "value": "Shipping to"}
            ]
        },
        {
            "filename": "intercepted_call_audio.mp3",
            "type": "audio",
            "summary": "Audio intercept #4451 dated 15-Dec-2025. Voice verification confirms speakers as 'Alias: Viper' and 'Banker_Steve'. Viper instructs Steve to 'clean' 500 BTC through 'ShellCorp_Global' accounts in Singapore by Friday.",
            "entities": [
                {"name": "Viper", "type": "Person"},
                {"name": "Banker_Steve", "type": "Person"},
                {"name": "ShellCorp_Global", "type": "Organization"},
                {"name": "Singapore", "type": "Location"}
            ],
            "links": [
                {"source": "Viper", "target": "Banker_Steve", "value": "Instructed"},
                {"source": "Banker_Steve", "target": "ShellCorp_Global", "value": "Manages accounts for"},
                {"source": "ShellCorp_Global", "target": "Singapore", "value": "Registered in"}
            ]
        },
        {
            "filename": "surveillance_meeting_photo.jpg",
            "type": "image",
            "summary": "Surveillance image taken at 'Café Noir', Paris. Identifies 'Kingpin' meeting with 'Politician_X'. Exchange of a black briefcase (Evidence #99) observed at 14:00 hours.",
            "entities": [
                {"name": "Kingpin", "type": "Person"},
                {"name": "Politician_X", "type": "Person"},
                {"name": "Café Noir", "type": "Location"},
                {"name": "Black Briefcase", "type": "Evidence"}
            ],
            "links": [
                {"source": "Kingpin", "target": "Politician_X", "value": "Met with"},
                {"source": "Kingpin", "target": "Black Briefcase", "value": "Handed over"},
                {"source": "Café Noir", "target": "Kingpin", "value": "Sighted at"}
            ]
        },
        {
            "filename": "crypto_ledger.csv",
            "type": "document",
            "summary": "CSV export of the 'Cold Wallet' ledger. Traces flow of 5000 BTC from 'DarkMarket_Wallet' -> 'Mixer_Service' -> 'ShellCorp_Global'. Final exit node IP traced to 'Server_Beta' in Switzerland.",
            "entities": [
                {"name": "DarkMarket_Wallet", "type": "Account"},
                {"name": "ShellCorp_Global", "type": "Organization"},
                {"name": "Server_Beta", "type": "Device"},
                {"name": "Switzerland", "type": "Location"}
            ],
            "links": [
                {"source": "DarkMarket_Wallet", "target": "ShellCorp_Global", "value": "Transferred funds to"},
                {"source": "ShellCorp_Global", "target": "Server_Beta", "value": "Controlled by"},
                {"source": "Server_Beta", "target": "Switzerland", "value": "Located in"}
            ]
        },
        {
            "filename": "confession_video.mp4",
            "type": "video",
            "summary": "Video confession of 'Mule_John'. Mentions he was recruited by 'Viper' to transport cash to 'The warehouse'. Confirms 'The warehouse' is used to store illegal arms.",
            "entities": [
                {"name": "Mule_John", "type": "Person"},
                {"name": "Viper", "type": "Person"},
                {"name": "The Warehouse", "type": "Location"}
            ],
            "links": [
                {"source": "Mule_John", "target": "Viper", "value": "Recruited by"},
                {"source": "Mule_John", "target": "The Warehouse", "value": "Transported cash to"}
            ]
        },
        {
            "filename": "gps_tracker_log.json",
            "type": "document",
            "summary": "GPS logs from the suspect vehicle (Reg: XX-99-YY). Shows repeated trips between 'The Warehouse' and 'Port 4' between 01:00 AM and 04:00 AM for the past month.",
            "entities": [
                {"name": "Vehicle XX-99-YY", "type": "Vehicle"},
                {"name": "The Warehouse", "type": "Location"},
                {"name": "Port 4", "type": "Location"}
            ],
            "links": [
                {"source": "Vehicle XX-99-YY", "target": "The Warehouse", "value": "Visited frequently"},
                {"source": "Vehicle XX-99-YY", "target": "Port 4", "value": "Visited frequently"},
                {"source": "The Warehouse", "target": "Port 4", "value": "Connected via transport route"}
            ]
        },
        {
            "filename": "bank_statement.pdf",
            "type": "document",
            "summary": "Official bank statement of 'ShellCorp_Global' showing receipt of $5M USD from 'Offshore_Holdings' and immediate wire transfer to 'Arms_Dealer_Inc'.",
            "entities": [
                {"name": "ShellCorp_Global", "type": "Organization"},
                {"name": "Offshore_Holdings", "type": "Organization"},
                {"name": "Arms_Dealer_Inc", "type": "Organization"}
            ],
            "links": [
                {"source": "Offshore_Holdings", "target": "ShellCorp_Global", "value": "Sent $5M"},
                {"source": "ShellCorp_Global", "target": "Arms_Dealer_Inc", "value": "Wired $5M"}
            ]
        }
    ]

    evidence_list_wrapped_1 = []
    
    for ev in evidence_items_1:
        evidence_id = str(uuid.uuid4())
        uploaded_at_str = datetime.now().isoformat()
        
        # Determine Graph
        kg = {
            "nodes": [], 
            "links": ev.get("links", [])
        }
        for ent in ev.get("entities", []):
            kg["nodes"].append({"id": ent["name"], "group": ent["type"]})

        # Metadata
        ev_meta = {
            "evidence_id": evidence_id,
            "case_id": case_id_1,
            "filename": ev["filename"],
            "content_type": "video/mp4" if ev["type"] == "video" else "application/pdf" if ev["type"] == "document" else "image/jpeg",
            "uploader": "Senior Detective",
            "uploader_role": "Forensics",
            "tx_hash": f"0x{uuid.uuid4().hex}", 
            "url": f"https://s3.amazonaws.com/bucket/{evidence_id}/{ev['filename']}",
            "uploaded_at": uploaded_at_str,
            "ai_summary": ev["summary"],
            "knowledge_graph": kg
        }
        
        # Wrapper
        ev_wrapper = {
            "id": evidence_id,
            "name": ev["filename"],
            "type": ev["type"],
            "uploadedAt": uploaded_at_str,
            "metadata": ev_meta
        }
        
        evidence_list_wrapped_1.append(ev_wrapper)
        evidence_table.put_item(Item=ev_meta)

    # Insert Case 1
    case_item_1 = {
        "id": case_id_1,
        "caseNumber": case_number_1,
        "district": "International Crime Unit",
        "unit": "Organized Crime Wing",
        "lawSections": ["PMLA Act", "Arms Act", "IPC 120B (Conspiracy)"],
        "dateOfOffence": (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
        "dateOfReport": (datetime.now() - timedelta(days=85)).strftime("%Y-%m-%d"),
        "sceneOfCrime": "Multiple Locations (Global)",
        "latitude": "46.2044", # Geneva approx
        "longitude": "6.1432",
        "description": description_1,
        "accused": [
            {"name": "The Kingpin", "status": "Wanted", "gender": "Male", "age": "55"},
            {"name": "Viper", "status": "Arrested", "gender": "Male", "age": "32"}
        ],
        "status": "Charge Sheet Filed",
        "createdAt": datetime.now().isoformat(),
        "updatedAt": datetime.now().isoformat(),
        "evidence": evidence_list_wrapped_1,
        "publicAlertEnabled": True,
        "publicAlertMessage": "Red Corner Notice issued for 'The Kingpin'.",
        "contrabandType": "Illegal Arms & Crypto",
        "contrabandQuantity": "$50M Value"
    }

    print(f"Adding Complex Case: {case_number_1}")
    cases_table.put_item(Item=case_item_1)
    print("✅ Complex Case 1 Added!")

    # --- CASE 2: Project Titan (Corporate Espionage) ---
    print("🚀 Adding COMPLEX Case 2: Project Titan...")
    case_id_2 = str(uuid.uuid4())
    case_number_2 = f"CR-CORP-2025-{random.randint(1000, 9999)}"
    
    description_2 = "Case 'Project Titan': Theft of proprietary autonomous vehicle algorithms from 'AutoDrive Inc'. The stolen IP was attempted to be sold to a foreign competitor 'RedStar Motors'. Involves insider threat and encrypted data exfiltration."
    
    evidence_items_2 = [
        {
            "filename": "server_access_logs_dec12.log",
            "type": "document",
            "summary": "Server access logs showing user 'Dev_Mark' accessing restricted directory '/src/lidar_core/' at 03:00 AM on a Sunday. Data exfiltration of 50GB detected via port 443.",
            "entities": [
                {"name": "Dev_Mark", "type": "Person"},
                {"name": "/src/lidar_core/", "type": "File"},
                {"name": "AutoDrive Server", "type": "Device"}
            ],
            "links": [
                {"source": "Dev_Mark", "target": "AutoDrive Server", "value": "Accessed at 03:00 AM"},
                {"source": "Dev_Mark", "target": "/src/lidar_core/", "value": "Downloaded"},
                {"source": "AutoDrive Server", "target": "Port 443", "value": "Exfiltrated Data via"}
            ]
        },
        {
            "filename": "encrypted_email_thread.txt",
            "type": "document",
            "summary": "Decrypted email thread between 'Dev_Mark' and 'Handler_Victor'. Mark confirms 'Payload is ready' and demands payment of 500k USDT. Victor replies with wallet address.",
            "entities": [
                {"name": "Dev_Mark", "type": "Person"},
                {"name": "Handler_Victor", "type": "Person"},
                {"name": "500k USDT", "type": "Evidence"},
                {"name": "Crypto Wallet", "type": "Account"}
            ],
            "links": [
                {"source": "Dev_Mark", "target": "Handler_Victor", "value": "Emailed"},
                {"source": "Dev_Mark", "target": "500k USDT", "value": "Demanded"},
                {"source": "Handler_Victor", "target": "Crypto Wallet", "value": "Provided Address"}
            ]
        },
        {
            "filename": "cctv_office_lobby.mp4",
            "type": "video",
            "summary": "CCTV footage identifying 'Handler_Victor' entering the AutoDrive Inc lobby as a guest signed in by 'Dev_Mark' two days prior to the breach.",
            "entities": [
                {"name": "Handler_Victor", "type": "Person"},
                {"name": "Dev_Mark", "type": "Person"},
                {"name": "AutoDrive Lobby", "type": "Location"}
            ],
            "links": [
                {"source": "Handler_Victor", "target": "AutoDrive Lobby", "value": "Entered"},
                {"source": "Dev_Mark", "target": "Handler_Victor", "value": "Signed in as Guest"}
            ]
        },
        {
            "filename": "source_code_fragment.c",
            "type": "document",
            "summary": "Recovered source code fragment found on a USB drive in 'Dev_Mark's' car. Matches the proprietary LIDAR processing logic of AutoDrive Inc (98% similarity).",
            "entities": [
                {"name": "USB Drive", "type": "Evidence"},
                {"name": "Dev_Mark", "type": "Person"},
                {"name": "LIDAR Logic", "type": "Evidence"}
            ],
            "links": [
                {"source": "Dev_Mark", "target": "USB Drive", "value": "Possessed"},
                {"source": "USB Drive", "target": "LIDAR Logic", "value": "Contained Stolen Code"}
            ]
        },
        {
            "filename": "flight_manifest_hk.pdf",
            "type": "document",
            "summary": "Flight manifest showing 'Handler_Victor' flew to Hong Kong one day after the data breach. Seat 4A, Flight CX-881.",
            "entities": [
                {"name": "Handler_Victor", "type": "Person"},
                {"name": "Hong Kong", "type": "Location"},
                {"name": "Flight CX-881", "type": "Evidence"}
            ],
            "links": [
                {"source": "Handler_Victor", "target": "Hong Kong", "value": "Traveled to"},
                {"source": "Handler_Victor", "target": "Flight CX-881", "value": "Passenger on"}
            ]
        },
        {
            "filename": "meeting_recording_jan12.wav",
            "type": "audio",
            "summary": "Audio recording from a bugged meeting room. 'CEO_RedStar' is heard discussing 'Upcoming acquisition of new tech' with 'Handler_Victor'.",
            "entities": [
                {"name": "CEO_RedStar", "type": "Person"},
                {"name": "Handler_Victor", "type": "Person"},
                {"name": "RedStar Motors", "type": "Organization"}
            ],
            "links": [
                {"source": "Handler_Victor", "target": "CEO_RedStar", "value": "Met with"},
                {"source": "CEO_RedStar", "target": "RedStar Motors", "value": "Leads"}
            ]
        },
        {
            "filename": "steg_image_cat.png",
            "type": "image",
            "summary": "Steganographic analysis of a seemingly harmless cat image sent by Mark reveals hidden zip archive password 'TitanFall2025'.",
            "entities": [
                {"name": "Cat Image", "type": "Evidence"},
                {"name": "Dev_Mark", "type": "Person"},
                {"name": "Password", "type": "Evidence"}
            ],
            "links": [
                {"source": "Dev_Mark", "target": "Cat Image", "value": "Sent"},
                {"source": "Cat Image", "target": "Password", "value": "Concealed"}
            ]
        },
        {
            "filename": "forensic_timeline_report.pdf",
            "type": "document",
            "summary": "Consolidated forensic report establishing the timeline of the insider threat, data staging, encryption, exfiltration, and recipient hand-off.",
            "entities": [
                {"name": "Dev_Mark", "type": "Person"},
                {"name": "Data Breach Incident", "type": "Incident"},
                {"name": "AutoDrive Inc", "type": "Organization"}
            ],
            "links": [
                {"source": "Dev_Mark", "target": "Data Breach Incident", "value": "Perpetrated"},
                {"source": "Data Breach Incident", "target": "AutoDrive Inc", "value": "Victim"}
            ]
        }
    ]

    evidence_list_wrapped_2 = []
    
    for ev in evidence_items_2:
        evidence_id = str(uuid.uuid4())
        uploaded_at_str = datetime.now().isoformat()
        
        # Determine Graph
        kg = {
            "nodes": [], 
            "links": ev.get("links", [])
        }
        for ent in ev.get("entities", []):
            kg["nodes"].append({"id": ent["name"], "group": ent["type"]})

        # Metadata
        ev_meta = {
            "evidence_id": evidence_id,
            "case_id": case_id_2,
            "filename": ev["filename"],
            "content_type": "video/mp4" if ev["type"] == "video" else "audio/wav" if ev["type"] == "audio" else "application/pdf" if ev["type"] == "document" else "image/png",
            "uploader": "IP Protection Unit",
            "uploader_role": "Forensics",
            "tx_hash": f"0x{uuid.uuid4().hex}", 
            "url": f"https://s3.amazonaws.com/bucket/{evidence_id}/{ev['filename']}",
            "uploaded_at": uploaded_at_str,
            "ai_summary": ev["summary"],
            "knowledge_graph": kg
        }
        
        # Wrapper
        ev_wrapper = {
            "id": evidence_id,
            "name": ev["filename"],
            "type": ev["type"],
            "uploadedAt": uploaded_at_str,
            "metadata": ev_meta
        }
        
        evidence_list_wrapped_2.append(ev_wrapper)
        evidence_table.put_item(Item=ev_meta)

    # Insert Case 2
    case_item_2 = {
        "id": case_id_2,
        "caseNumber": case_number_2,
        "district": "Tech Park Zone",
        "unit": "Economic Offences Wing",
        "lawSections": ["IT Act Sec 66", "Corporate Espionage Act", "Breach of Contract"],
        "dateOfOffence": (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d"),
        "dateOfReport": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
        "sceneOfCrime": "AutoDrive Inc HQ, Server Room",
        "latitude": "37.3861", # Silicon Valley approx
        "longitude": "-122.0839",
        "description": description_2,
        "accused": [
            {"name": "Mark 'Dev_Mark' Sullivan", "status": "Terminated", "gender": "Male", "age": "29"},
            {"name": "Victor 'Handler' Kovac", "status": "Wanted (Red Corner)", "gender": "Male", "age": "45"}
        ],
        "status": "Under Investigation",
        "createdAt": datetime.now().isoformat(),
        "updatedAt": datetime.now().isoformat(),
        "evidence": evidence_list_wrapped_2,
        "publicAlertEnabled": False,
        "contrabandType": "Source Code & Algorithms",
        "contrabandQuantity": "50 GB"
    }

    print(f"Adding Second Complex Case: {case_number_2}")
    cases_table.put_item(Item=case_item_2)
    print("✅ Complex Case 2 Added!")

if __name__ == "__main__":
    run()
