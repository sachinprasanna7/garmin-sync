import os
import json
from dotenv import load_dotenv
from fatsecret import Fatsecret

# Note: Adjust path if running locally vs in Docker
load_dotenv("secrets/.env")

def setup():
    key = os.getenv("FATSECRET_KEY")
    secret = os.getenv("FATSECRET_SECRET")
    
    fs = Fatsecret(key, secret)
    
    # 1. Generate the Auth URL
    auth_url = fs.get_authorize_url()
    print("\n🌐 1. Open this URL in your browser:")
    print(auth_url)
    
    # 2. You log in, click "Allow", and it gives you a PIN
    pin = input("\n🔢 2. Enter the PIN provided by FatSecret: ")
    
    # 3. Exchange PIN for permanent tokens
    session_token = fs.authenticate(pin)
    
    # 4. Save tokens to our secrets folder
    with open("secrets/fs_token.json", "w") as f:
        json.dump(session_token, f)
        
    print("✅ FatSecret Access Tokens saved to fs_token.json!")

if __name__ == "__main__":
    setup()