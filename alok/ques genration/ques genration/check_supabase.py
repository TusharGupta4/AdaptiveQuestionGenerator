import os
import sys
import time
from pathlib import Path

# Fix Windows console encoding if needed
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

def check_supabase():
    console.print(Panel.fit("[bold cyan]Supabase Cloud Connectivity & Status Check[/bold cyan]"))

    from app.core.config import settings
    from app.core.supabase import check_supabase_connection, get_supabase_client
    from app.core.database import engine, db_url

    # 1. Environment Variables & URL Detection
    url = settings.effective_supabase_url
    key = settings.effective_supabase_key

    if not url:
        console.print("[bold red][ERROR] Supabase URL is not configured in .env or environment variables![/bold red]")
        console.print("[yellow]Please provide NEXT_PUBLIC_SUPABASE_URL or SUPABASE_URL in .env[/yellow]")
        return False

    console.print(f"[bold green][OK][/bold green] Supabase URL detected: [cyan]{url}[/cyan]")

    if not key:
        console.print("[bold yellow][WARNING] Supabase Key is missing or empty.[/bold yellow]")
    else:
        masked_key = key[:10] + "..." + key[-6:] if len(key) > 16 else key[:4] + "..."
        console.print(f"[bold green][OK][/bold green] Supabase Key detected: [yellow]{masked_key}[/yellow]")

    # 2. Connection and Health Diagnostics
    console.print("\n[cyan]Pinging Supabase services...[/cyan]")
    diag = check_supabase_connection()

    table = Table(title="Supabase Diagnostics Report")
    table.add_column("Property", style="bold cyan")
    table.add_column("Value", style="bold white")

    table.add_row("Project Reference", diag.get("project_ref") or "N/A")
    table.add_row("Endpoint URL", diag.get("url") or "N/A")
    table.add_row("Key Type", diag.get("key_type") or "N/A")
    
    latency = f"{diag.get('latency_ms')} ms" if diag.get('latency_ms') else "N/A"
    table.add_row("Network Latency", latency)

    auth_style = "[green]ONLINE[/green]" if diag.get("auth_status") == "ONLINE" else f"[red]{diag.get('auth_status')}[/red]"
    table.add_row("Auth Service (GoTrue)", auth_style)

    storage_style = "[green]ONLINE[/green]" if diag.get("storage_status") == "ONLINE" else f"[yellow]{diag.get('storage_status')}[/yellow]"
    table.add_row("Storage Service", storage_style)

    bucket_names = ", ".join(diag.get("buckets", [])) if diag.get("buckets") else "None (default)"
    table.add_row("Active Storage Buckets", bucket_names)

    # Database info
    db_type = "PostgreSQL (Supabase Cloud)" if db_url.startswith("postgresql") else f"SQLite Local ({Path(db_url.split('///')[-1]).name if '///' in db_url else db_url})"
    table.add_row("SQLAlchemy Database", db_type)

    overall_status = "[bold green]ACTIVE AND WORKING[/bold green]" if diag.get("connected") else "[bold red]FAILED[/bold red]"
    table.add_row("Overall Status", overall_status)

    console.print(table)

    # 3. Test SDK Client Instance
    console.print("\n[cyan]Verifying Python Supabase SDK Client instance...[/cyan]")
    client = get_supabase_client()
    if client:
        console.print("[bold green][OK] Supabase SDK Client successfully initialized and ready for cloud operations![/bold green]")
    else:
        console.print("[bold red][ERROR] Failed to instantiate Supabase SDK client.[/bold red]")
        return False

    if diag.get("connected"):
        console.print(f"\n[bold green][SUCCESS] {diag.get('message')}[/bold green]")
        return True
    else:
        console.print(f"\n[bold red][FAILURE] {diag.get('message')}[/bold red]")
        return False

if __name__ == "__main__":
    success = check_supabase()
    sys.exit(0 if success else 1)
