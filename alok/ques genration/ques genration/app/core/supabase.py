"""
Supabase client provider, connection health verification, and cloud utilities.
"""

import time
import os
from typing import Optional, Dict, Any, List
import requests

from app.core.config import settings

# Global client cache
_supabase_client = None

def get_supabase_client():
    """
    Returns an initialized Supabase Client instance or None if not configured.
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    url = settings.effective_supabase_url
    key = settings.effective_supabase_key

    if not url or not key:
        return None

    try:
        from supabase import create_client, ClientOptions
        _supabase_client = create_client(url, key)
        return _supabase_client
    except Exception as e:
        print(f"[Supabase] Error initializing Supabase client: {e}")
        return None


def check_supabase_connection() -> Dict[str, Any]:
    """
    Performs comprehensive connectivity and health checks for the Supabase instance.
    Returns a status dictionary with diagnostics.
    """
    url = settings.effective_supabase_url
    key = settings.effective_supabase_key

    if not url:
        return {
            "connected": False,
            "status": "NOT_CONFIGURED",
            "message": "Supabase URL is missing from environment variables.",
            "url": None,
            "project_ref": None,
            "latency_ms": None,
            "auth_status": "OFFLINE",
            "storage_status": "OFFLINE",
            "buckets": [],
            "key_type": None
        }

    # Extract project ref from URL
    # e.g. https://nfszfnjsrhmobjikliqk.supabase.co -> nfszfnjsrhmobjikliqk
    clean_url = url.strip().rstrip("/")
    project_ref = clean_url.replace("https://", "").replace("http://", "").split(".")[0]

    key_type = "Publishable / Anon" if key.startswith("sb_publishable_") or "publishable" in key.lower() else "Service Role / Custom"

    result = {
        "connected": False,
        "status": "UNKNOWN",
        "message": "",
        "url": clean_url,
        "project_ref": project_ref,
        "latency_ms": None,
        "auth_status": "UNKNOWN",
        "storage_status": "UNKNOWN",
        "buckets": [],
        "key_type": key_type
    }

    start_time = time.time()

    headers = {}
    if key:
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}"
        }

    # 1. Ping Auth endpoint
    try:
        auth_resp = requests.get(f"{clean_url}/auth/v1/health", headers=headers, timeout=6.0)
        latency = round((time.time() - start_time) * 1000, 2)
        result["latency_ms"] = latency
        if auth_resp.status_code == 200:
            result["auth_status"] = "ONLINE"
        else:
            result["auth_status"] = f"HTTP_{auth_resp.status_code}"
    except Exception as e:
        result["auth_status"] = f"ERROR: {str(e)}"

    # 2. Test Supabase Python Client & Storage
    client = get_supabase_client()
    if client:
        try:
            buckets = client.storage.list_buckets()
            result["storage_status"] = "ONLINE"
            result["buckets"] = [b.name for b in buckets] if hasattr(buckets, "__iter__") else []
            result["connected"] = True
            result["status"] = "ACTIVE_AND_WORKING"
            result["message"] = f"Successfully connected to Supabase project ({project_ref})! Auth & Storage services are operational."
        except Exception as e:
            # Fallback to direct HTTP check
            try:
                storage_resp = requests.get(f"{clean_url}/storage/v1/bucket", headers=headers, timeout=6.0)
                if storage_resp.status_code == 200:
                    result["storage_status"] = "ONLINE"
                    result["connected"] = True
                    result["status"] = "ACTIVE_AND_WORKING"
                    result["message"] = f"Connected to Supabase project ({project_ref}) via REST API. Storage service active."
                else:
                    result["storage_status"] = f"HTTP_{storage_resp.status_code}"
                    result["status"] = "DEGRADED"
                    result["message"] = f"Supabase responded with storage status code {storage_resp.status_code}."
            except Exception as se:
                result["storage_status"] = f"ERROR: {str(se)}"
                result["status"] = "CONNECTION_ERROR"
                result["message"] = f"Storage endpoint unreachable: {str(se)}"
    else:
        if result["auth_status"] == "ONLINE":
            result["connected"] = True
            result["status"] = "ACTIVE_BASIC"
            result["message"] = f"Supabase project reachable at {clean_url}. Supabase SDK client not initialized."
        else:
            result["status"] = "FAILED"
            result["message"] = "Unable to establish connection to Supabase endpoint."

    return result
