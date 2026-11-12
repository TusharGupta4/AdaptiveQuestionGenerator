"""
Supabase Cloud Service for Adaptive Exam Engine.
Provides high-level cloud integrations:
- Health and status monitoring
- Cloud Storage operations (exam papers, answer sheets, OCR assets)
- Cloud backup & telemetry helpers
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from app.core.config import settings
from app.core.supabase import get_supabase_client, check_supabase_connection

class SupabaseService:
    @staticmethod
    def get_status() -> Dict[str, Any]:
        """Returns the real-time Supabase connection and service status."""
        return check_supabase_connection()

    @staticmethod
    def is_active() -> bool:
        """Returns True if Supabase is configured and reachable."""
        res = check_supabase_connection()
        return res.get("connected", False)

    @staticmethod
    def list_buckets() -> List[str]:
        """Lists available storage buckets in Supabase."""
        client = get_supabase_client()
        if not client:
            return []
        try:
            buckets = client.storage.list_buckets()
            return [b.name for b in buckets] if hasattr(buckets, "__iter__") else []
        except Exception:
            return []

    @staticmethod
    def upload_file_to_storage(
        bucket_name: str,
        destination_path: str,
        file_bytes: bytes,
        content_type: str = "text/html"
    ) -> Dict[str, Any]:
        """
        Uploads a file (e.g. generated HTML paper or student submission) to Supabase Storage.
        Returns a dict with success status and public/resource URL.
        """
        client = get_supabase_client()
        if not client:
            return {"success": False, "error": "Supabase client not initialized"}

        try:
            # Upload using storage client
            res = client.storage.from_(bucket_name).upload(
                path=destination_path,
                file=file_bytes,
                file_options={"content-type": content_type, "upsert": "true"}
            )
            
            # Retrieve public URL
            public_url = client.storage.from_(bucket_name).get_public_url(destination_path)
            return {
                "success": True,
                "path": destination_path,
                "public_url": public_url,
                "response": str(res)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "hint": "Ensure the bucket exists in your Supabase dashboard under Storage with public access enabled."
            }

    @staticmethod
    def upload_paper_artifact(paper_id: int, html_content: str, bucket_name: str = "exam-papers") -> Dict[str, Any]:
        """Uploads a generated exam paper HTML to Supabase storage."""
        dest = f"papers/paper_{paper_id}.html"
        return SupabaseService.upload_file_to_storage(
            bucket_name=bucket_name,
            destination_path=dest,
            file_bytes=html_content.encode("utf-8"),
            content_type="text/html"
        )
