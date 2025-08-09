"""
Add test credits to user account
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.supabase_client import supabase_client

def add_credits_to_user():
    """Add credits to test user"""
    print("💰 Adding test credits...")
    
    try:
        service_client = supabase_client.get_client(use_service_key=True)
        
        # Find the test user
        user_response = service_client.table('user_profiles').select('*').eq('email', 'sigorta.test2025@hotmail.com').execute()
        
        if not user_response.data:
            print("❌ Test user not found!")
            return
            
        user_id = user_response.data[0]['id']
        print(f"👤 Found user: {user_response.data[0]['email']}")
        
        # Check if credit balance exists
        credit_response = service_client.table('user_credit_balance').select('*').eq('user_id', user_id).execute()
        
        if credit_response.data:
            # Update existing balance
            current_balance = credit_response.data[0]['current_balance']
            new_balance = current_balance + 100
            
            update_response = service_client.table('user_credit_balance').update({
                'current_balance': new_balance
            }).eq('user_id', user_id).execute()
            
            print(f"✅ Updated balance: {current_balance} → {new_balance} credits")
        else:
            # Create new credit balance (simplified)
            insert_response = service_client.table('user_credit_balance').insert({
                'user_id': user_id,
                'current_balance': 100
            }).execute()
            
            print(f"✅ Created new credit balance: 100 credits")
            
        print("🎉 Credits added successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    add_credits_to_user()