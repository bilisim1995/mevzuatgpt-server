"""
Bypass credit system temporarily for testing
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Search through codebase for credit-related code
def find_credit_files():
    """Find files that handle credits"""
    print("🔍 Looking for credit-related files...")
    
    import glob
    
    credit_files = []
    
    # Search in services directory
    for file_path in glob.glob("services/*.py"):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'credit' in content.lower() or 'balance' in content.lower():
                credit_files.append(file_path)
                print(f"Found: {file_path}")
    
    # Search in API directory  
    for file_path in glob.glob("api/*/*.py"):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'insufficient_credits' in content or 'credit' in content.lower():
                credit_files.append(file_path)
                print(f"Found: {file_path}")
                
    return credit_files

if __name__ == "__main__":
    find_credit_files()