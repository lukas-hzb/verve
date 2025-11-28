
from app import create_app
from app.services import UserService, VocabService
from app.firestore_db import get_db

def debug_firestore():
    app = create_app('development')
    
    with app.app_context():
        print("--- Debugging Firestore ---")
        
        # 1. Create User
        print("\n1. Creating User...")
        try:
            # Cleanup
            try:
                existing = UserService.authenticate_user("debug_user", "password")
                UserService.delete_user(existing.id)
            except:
                pass
                
            user = UserService.create_user("debug_user", "debug@test.com", "password")
            print(f"User created: {user.id}")
        except Exception as e:
            print(f"Error creating user: {e}")
            return

        # 2. Check Default Set
        print("\n2. Checking Default Set...")
        try:
            sets = VocabService.get_all_set_names(user.id)
            default_set = next((s for s in sets if s['name'] == "Hauptstädte"), None)
            
            if default_set:
                print(f"Default set found: {default_set['id']}")
                print(f"Card count in summary: {default_set['card_count']}")
                
                # Fetch full set
                vset = VocabService.get_vocab_set(default_set['id'], user.id)
                print(f"Cards in loaded set: {len(vset.cards)}")
                for c in vset.cards[:3]:
                    print(f" - {c.front} -> {c.back} (SetID: {c.vocab_set_id})")
            else:
                print("Default set NOT found")
        except Exception as e:
            print(f"Error checking default set: {e}")
            import traceback
            traceback.print_exc()

        # 3. Create New Set & Add Card
        print("\n3. Creating New Set & Adding Card...")
        try:
            new_set = VocabService.create_user_set(user.id, "Debug Set")
            print(f"New set created: {new_set.id}")
            
            card = VocabService.add_card(new_set.id, "Debug Front", "Debug Back", user.id)
            print(f"Card added: {card.id}")
            
            # Verify
            vset_debug = VocabService.get_vocab_set(new_set.id, user.id)
            print(f"Cards in debug set: {len(vset_debug.cards)}")
            if len(vset_debug.cards) > 0:
                print(f" - {vset_debug.cards[0].front}")
            else:
                print("Card NOT found in debug set!")
                
        except Exception as e:
            print(f"Error adding card: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_firestore()
