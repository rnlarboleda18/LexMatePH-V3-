import time
import datetime
import psycopg2
import os
import collections
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.console import Console

# --- Configuration ---
TARGET_FILE = 'grok_phase3_ids.txt'
DB_CONN_STR = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
HISTORY_LEN = 40  # How many data points for the graph

def get_db_connection():
    return psycopg2.connect(DB_CONN_STR)

def load_targets():
    if not os.path.exists(TARGET_FILE):
        return []
    with open(TARGET_FILE, 'r') as f:
        ids = [x.strip() for x in f.read().strip().split(',') if x.strip()]
    return [int(x) for x in ids if x.isdigit()]

def get_progress(target_ids):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = "SELECT count(*) FROM sc_decided_cases WHERE id = ANY(%s) AND ai_model = 'grok-4-1-fast-reasoning'"
        cur.execute(query, (target_ids,))
        count = cur.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

def generate_graph(history):
    """Generates a simple ascii bar chart from a list of values (0-100 normalized)."""
    if not history:
        return Text("Waiting for data...", style="dim")
    
    max_val = max(history) if max(history) > 0 else 1
    # Heights:  ▂▃▄▅▆▇█
    chars = " ▂▃▄▅▆▇█"
    
    graph_str = ""
    for val in history:
        normalized = val / max_val
        index = int(normalized * (len(chars) - 1))
        graph_str += chars[index]
    
    return Text(graph_str, style="bold cyan")

def make_layout():
    layout = Layout(name="root")
    layout.split(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=3)
    )
    layout["main"].split_row(
        Layout(name="stats", ratio=1),
        Layout(name="graph", ratio=1)
    )
    return layout

def main():
    console = Console()
    target_ids = load_targets()
    total_cases = len(target_ids)
    
    if total_cases == 0:
        console.print("[red]No target file found or empty.[/red]")
        return

    # Tracking
    speed_history = collections.deque(maxlen=HISTORY_LEN)
    start_time = datetime.datetime.now().replace(hour=23, minute=15, second=0, microsecond=0)
    
    # Progress Bar Instance
    job_progress = Progress(
        "{task.description}",
        SpinnerColumn(),
        BarColumn(bar_width=None),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
    )
    task_id = job_progress.add_task("[green]Processing...", total=total_cases)

    # Live Loop
    layout = make_layout()
    
    with Live(layout, refresh_per_second=1, screen=True) as live:
        while True:
            # 1. Fetch Data
            completed = get_progress(target_ids)
            now = datetime.datetime.now()
            
            # 2. Calc Stats
            if now < start_time: start_time = now
            elapsed_min = (now - start_time).total_seconds() / 60.0
            if elapsed_min < 0.1: elapsed_min = 0.1
            
            rate = completed / elapsed_min # cases/min
            remaining = total_cases - completed
            
            speed_history.append(rate)
            
            # 3. Update Progress Bar
            job_progress.update(task_id, completed=completed)
            
            # 4. Build Components
            
            # Header
            header = Panel(
                Align.center(f"[bold white]GROK PHASE 3 FLEET MONITOR[/bold white] | {now.strftime('%H:%M:%S')}"),
                style="on blue"
            )
            
            # Stats Table
            stats_table = Table(show_header=False, expand=True, box=None)
            stats_table.add_row("Total Cases", f"[bold]{total_cases:,}[/bold]")
            stats_table.add_row("Completed", f"[bold green]{completed:,}[/bold]")
            stats_table.add_row("Remaining", f"[bold yellow]{remaining:,}[/bold]")
            stats_table.add_row("Speed", f"[bold cyan]{rate:.1f} cases/min[/bold]")
            
            if rate > 0:
                etf_min = remaining / rate
                etf_dt = now + datetime.timedelta(minutes=etf_min)
                etf_str = f"[bold green]{etf_dt.strftime('%I:%M %p')}[/bold]"
            else:
                etf_str = "Calculating..."
            stats_table.add_row("Est. Completion", etf_str)

            stats_panel = Panel(
                stats_table, 
                title="[bold]Statistics[/bold]", 
                border_style="green"
            )

            # Graph Panel
            graph_content = Align.center(
                generate_graph(speed_history), 
                vertical="middle"
            )
            graph_panel = Panel(
                graph_content,
                title=f"[bold]Speed Trend (Last {HISTORY_LEN} updates)[/bold]",
                border_style="cyan"
            )
            
            # Footer
            footer_content = job_progress
            
            # Compose Layout
            layout["header"].update(header)
            layout["stats"].update(stats_panel)
            layout["graph"].update(graph_panel)
            layout["footer"].update(Panel(footer_content, title="Overall Progress", border_style="blue"))
            
            time.sleep(2) # Update every 2s

if __name__ == "__main__":
    main()
