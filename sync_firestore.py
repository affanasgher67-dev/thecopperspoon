import firebase_admin
from firebase_admin import credentials, firestore
from pathlib import Path
import sys

# Add src to path so we can import restaurant_agent
sys.path.append(str(Path(__file__).resolve().parent / "src"))

from restaurant_agent.menu import _default_menu_payload

def sync_menu():
    key_path = Path(__file__).resolve().parent / "firebase-key.json"
    if not key_path.exists():
        print(f"Error: Firebase key not found at {key_path}")
        return

    cred = credentials.Certificate(str(key_path))
    firebase_admin.initialize_app(cred)
    db = firestore.client()

    payload = _default_menu_payload()
    
    # 1. Update metadata
    print("Updating menu metadata...")
    db.collection("metadata").document("menu").set({
        "restaurant": payload["restaurant"],
        "currency": payload["currency"],
        "updated_at": payload["updated_at"]
    })

    # 2. Update sections
    print("Updating menu sections...")
    sections_ref = db.collection("menu_sections")
    
    # Delete existing sections first to be clean
    docs = sections_ref.stream()
    for doc in docs:
        doc.reference.delete()
        
    for section in payload["sections"]:
        # Use a slugified name as doc ID
        doc_id = section["name"].lower().replace(" ", "_")
        sections_ref.document(doc_id).set(section)
        print(f"  Synced section: {section['name']}")

    print("Success: Firestore menu sync complete.")

if __name__ == "__main__":
    sync_menu()
