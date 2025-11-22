import requests
import sys
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8080"
EMAIL = f"test_restore_{int(time.time())}@example.com"
PASSWORD = "password123"

def log(msg):
    with open("test_output.txt", "a") as f:
        f.write(f"[TEST] {msg}\n")
    print(f"[TEST] {msg}")

def run_test():
    session = requests.Session()
    
    # 1. Register
    log("Registering user...")
    resp = session.post(f"{BASE_URL}/auth/register", data={
        "username": "test_restore",
        "email": EMAIL,
        "password": PASSWORD,
        "confirm_password": PASSWORD
    })
    if resp.status_code != 200:
        log(f"Registration failed: {resp.status_code}")
        return False
        
    # 2. Login
    log("Logging in...")
    resp = session.post(f"{BASE_URL}/auth/login", data={
        "email": EMAIL,
        "password": PASSWORD
    })
    if resp.status_code != 200:
        log(f"Login failed: {resp.status_code}")
        return False
        
    # 3. Create Set
    log("Creating set...")
    resp = session.post(f"{BASE_URL}/api/vocab_sets", json={"name": "Restore Test Set"})
    if resp.status_code != 201:
        log(f"Create set failed: {resp.status_code}")
        return False
    set_id = resp.json()['id']
    
    # 4. Add Card
    log("Adding card...")
    card_front = "Test Front"
    resp = session.post(f"{BASE_URL}/set/{set_id}/add_card", json={
        "front": card_front,
        "back": "Test Back"
    })
    if resp.status_code != 200:
        log(f"Add card failed: {resp.status_code}")
        return False
    
    # 5. Rate Card (Change state)
    log("Rating card...")
    resp = session.post(f"{BASE_URL}/api/update_card", json={
        "set_id": set_id,
        "card_front": card_front,
        "quality": 5 # Knew it perfectly
    })
    if resp.status_code != 200:
        log(f"Rate card failed: {resp.status_code}")
        return False
    
    updated_card = resp.json()['card']
    log(f"Card level after rating: {updated_card['level']}")
    if updated_card['level'] <= 1:
        log("Card level did not increase!")
        return False
        
    # 6. Restore Card
    log("Restoring card...")
    # We want to restore it to level 1 and now()
    original_next_review = datetime.now().isoformat()
    resp = session.post(f"{BASE_URL}/api/restore_card", json={
        "set_id": set_id,
        "card_front": card_front,
        "level": 1,
        "next_review": original_next_review
    })
    if resp.status_code != 200:
        log(f"Restore card failed: {resp.status_code} - {resp.text}")
        return False
        
    # 7. Verify Restoration
    log("Verifying restoration...")
    resp = session.get(f"{BASE_URL}/api/set/{set_id}/cards")
    cards = resp.json()['cards']
    target_card = next((c for c in cards if c['front'] == card_front), None)
    
    if not target_card:
        log("Card not found!")
        return False
        
    log(f"Card level after restore: {target_card['level']}")
    if target_card['level'] != 1:
        log(f"Card level mismatch! Expected 1, got {target_card['level']}")
        return False
        
    log("Test Passed!")
    return True

if __name__ == "__main__":
    try:
        if run_test():
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        log(f"Exception: {e}")
        sys.exit(1)
