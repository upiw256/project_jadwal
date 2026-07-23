#!/usr/bin/env python3
"""
Validate OAuth client_secret.json configuration for jadwal app.
Run on server: python3 validate_oauth.py
"""

import json
import sys
import os

def validate_oauth_config():
    client_secret_path = 'client_secret.json'
    
    # Check file exists
    if not os.path.exists(client_secret_path):
        print(f"✗ ERROR: {client_secret_path} tidak ditemukan")
        return False
    
    # Load JSON
    try:
        with open(client_secret_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"✗ ERROR: JSON parsing failed: {e}")
        return False
    except Exception as e:
        print(f"✗ ERROR: Cannot read file: {e}")
        return False
    
    # Check client type
    if 'web' not in data and 'installed' not in data:
        print("✗ ERROR: client_secret.json harus memiliki key 'web' atau 'installed'")
        print(f"   Keys yang ada: {list(data.keys())}")
        return False
    
    client_type = 'web' if 'web' in data else 'installed'
    client_info = data.get(client_type, {})
    
    # Print current config
    print(f"\n{'='*60}")
    print(f"OAuth Configuration Check")
    print(f"{'='*60}\n")
    
    print(f"Client Type: {client_type}")
    if client_type == 'installed':
        print("⚠ WARNING: Tipe 'installed' untuk desktop apps")
        print("  → Sebaiknya gunakan 'web' untuk web apps")
    
    client_id = client_info.get('client_id')
    if client_id:
        print(f"Client ID: {client_id[:30]}...")
    else:
        print("✗ ERROR: client_id tidak ditemukan")
        return False
    
    auth_uri = client_info.get('auth_uri')
    print(f"Auth URI: {auth_uri}")
    
    redirect_uris = client_info.get('redirect_uris', [])
    print(f"\nRedirect URIs ({len(redirect_uris)}):")
    if not redirect_uris:
        print("  ✗ EMPTY - Harus ada minimal 1 redirect URI")
        print(f"     Expected: https://jadwal.sman1margaasih.sch.id/")
        return False
    
    expected = "https://jadwal.sman1margaasih.sch.id/"
    for uri in redirect_uris:
        match = "✓" if uri == expected else "⚠"
        print(f"  {match} {uri}")
    
    if expected not in redirect_uris:
        print(f"\n✗ WARNING: Expected redirect URI '{expected}' tidak ditemukan")
        print(f"   Make sure you add this to Authorized redirect URIs in Google Cloud Console")
        return False
    
    print(f"\n{'='*60}")
    print("✓ Configuration looks good!")
    print(f"{'='*60}\n")
    return True

if __name__ == '__main__':
    success = validate_oauth_config()
    sys.exit(0 if success else 1)
