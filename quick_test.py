import sys
print(f"Using Python: {sys.executable}")

try:
    import requests
    print("✓ requests imported successfully")
except ImportError as e:
    print(f"✗ requests import failed: {e}")

try:
    import discord
    print("✓ discord.py imported successfully")  
except ImportError as e:
    print(f"✗ discord.py import failed: {e}")