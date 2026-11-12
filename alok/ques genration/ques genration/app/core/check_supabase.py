from rich.console import Console
from rich.panel import Panel
from sqlalchemy import text
from app.core.database import engine
from app.core.config import settings

console = Console()

def check_connection():
    console.print(Panel("[bold cyan]Testing Supabase Cloud Database Connection[/bold cyan]"))

    masked_url = settings.DATABASE_URL
    if "@" in masked_url:
        prefix, host = masked_url.split("@")
        masked_url = f"{prefix.split(':')[0]}://****:****@{host}"

    console.print(f"Connecting to: [yellow]{masked_url}[/yellow]\n")

    try:
        with engine.connect() as conn:
            # 1. Fetch Postgres version
            result = conn.execute(text("SELECT version();"))
            pg_version = result.scalar()

            # 2. Fetch Current Database & User
            db_info = conn.execute(text("SELECT current_database(), current_user;")).fetchone()
            
            console.print("[bold green]✅ Connection Successful![/bold green]")
            console.print(f"📦 [bold]PostgreSQL Version:[/bold] {pg_version[:65]}...")
            console.print(f"🗄️  [bold]Database Name:[/bold] {db_info[0]}")
            console.print(f"👤 [bold]Connected As User:[/bold] {db_info[1]}")

            # 3. Check existing tables
            tables_query = conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
            ))
            existing_tables = [row[0] for row in tables_query.fetchall()]
            
            if existing_tables:
                console.print(f"\n📋 [bold]Existing Tables in Supabase ({len(existing_tables)}):[/bold] {', '.join(existing_tables)}")
            else:
                console.print("\nℹ️  [yellow]No tables found in public schema yet. Ready to initialize tables![/yellow]")

    except Exception as e:
        console.print(f"[bold red]❌ Connection Failed:[/bold red] {e}")
        console.print("\n[yellow]Troubleshooting Checklist:[/yellow]")
        console.print("1. Password galat ho sakta hai ya special characters URL-encode nahi huye.")
        console.print("2. Port check karein (Session Pooler: 5432 ya 6543).")
        console.print("3. URL ke aage '?sslmode=require' zaroor laga ho.")

if __name__ == "__main__":
    check_connection()     