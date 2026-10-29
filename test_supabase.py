"""Test script for Supabase API connection in AgriDoc Liberia project."""

import os
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Load environment variables from .env file using python-dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv is not available, read .env manually
    pass

# Read Supabase credentials from environment
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_PUBLISHABLE_KEY")

# Validate that both values exist
if not supabase_url:
    print("Error: SUPABASE_URL not found in environment variables.")
    sys.exit(1)

if not supabase_key:
    print("Error: SUPABASE_PUBLISHABLE_KEY not found in environment variables.")
    sys.exit(1)

# Supabase Auth settings endpoint
api_endpoint = f"{supabase_url}/auth/v1/settings"

# Create request with publishable key in apikey header
request = Request(api_endpoint, headers={"apikey": supabase_key})

try:
    # Send GET request with 10-second timeout
    response = urlopen(request, timeout=10)
    print(f"Success! HTTP Status Code: {response.status}")

except HTTPError as e:
    # Handle HTTP errors
    print(f"HTTP Error: {e.code}")
    if e.code == 401:
        print("Failure: Unauthorized - check that SUPABASE_PUBLISHABLE_KEY is correct")
    elif e.code == 403:
        print("Failure: Forbidden - the key lacks permission for this endpoint")
    elif e.code == 404:
        print("Failure: Not found - check SUPABASE_URL and endpoint path")
    else:
        print(f"Failure: HTTP status {e.code} received")

except URLError as e:
    # Handle network errors
    print(f"Network Error: {e.reason}")
    print("Could not connect to Supabase URL - verify SUPABASE_URL is correct")

except Exception as e:
    # Handle any other unexpected errors
    print(f"Error: {type(e).__name__} - {e}")