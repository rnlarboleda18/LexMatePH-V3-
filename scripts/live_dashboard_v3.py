import time
import datetime
import psycopg2
import os
import collections
import sys
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.console import Console

# --- Configuration ---
# 1. We assume ONLY this fleet is using 'grok-4-1-fast-reasoning' currently, 
#    or that we just want a total count of that model.
#    This avoids sending 37k IDs over the wire every second.
QUERY_OPTIMIZED = "SELECT count(*) FROM sc_decided_cases WHERE ai_model = 'grok-4-1-fast-reasoning'"
DB_CONN_STR = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
HISTORY_LEN = 60  

def get_db_connection():
    return psycopg2.connect(DB_CONN_STR)

def load_target_count():
    # Only need the total count, not the list, for the status bar
    target_file = 'grok_phase3_ids.txt'
    if not os.path.exists(target_file):
        return 36941 # Fallback known value
    with open(target_file, 'r') as f:
        # Fast count
        return f.read().count(',') + 1

def generate_graph(history):
    if not history:
        return Text("Collecting data...", style="dim")
    max_val = max(history) if max(history) > 0 else 1
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
    total_cases = load_target_count()
    
    # Pre-fill layout to avoid empty placeholders
    layout = make_layout()
    layout["header"].update(Panel(Align.center("Initializing Monitor..."), style="on blue"))
    layout["stats"].update(Panel("Connecting to Database...", title="Stats"))
    layout["graph"].update(Panel("Waiting for history...", title="Speed"))
    layout["footer"].update(Panel("Loading...", title="Progress"))

    speed_history = collections.deque(maxlen=HISTORY_LEN)
    # Phase 3 start approx
    start_time = datetime.datetime.now().replace(hour=23, minute=15, second=0, microsecond=0)
    
    # Init Progress Bar
    job_progress = Progress(
        "{task.description}",
        SpinnerColumn(),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        expand=True
    )
    task_id = job_progress.add_task("[green]Processing...", total=total_cases)

    # Start Live
    with Live(layout, refresh_per_second=4, screen=True) as live:
        while True:
            try:
                # 1. DB Query (Fast)
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(QUERY_OPTIMIZED)
                completed = cur.fetchone()[0]
                conn.close()
                
                # 2. Stats
                now = datetime.datetime.now()
                if now < start_time: start_time = now
                elapsed_min = (now - start_time).total_seconds() / 60.0
                if elapsed_min < 0.1: elapsed_min = 0.1
                
                rate = completed / elapsed_min
                remaining = total_cases - completed
                
                speed_history.append(rate)
                
                # 3. Update Components
                header = Panel(
                    Align.center(f"[bold white]GROK PHASE 3 FLEET MONITOR[/bold white] | {now.strftime('%H:%M:%S')}"),
                    style="on blue"
                )
                
                stats_table = Table(show_header=False, expand=True, box=None, padding=(0,1))
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
                
                stats_panel = Panel(stats_table, title="[bold]Statistics[/bold]", border_style="green")
                
                graph_panel = Panel(
                    Align.center(generate_graph(speed_history), vertical="middle"),
                    title="[bold]Speed Trend[/bold]",
                    border_style="cyan"
                )
                
                job_progress.update(task_id, completed=completed)
                footer_panel = Panel(job_progress, title="Overall Progress", border_style="blue")
                
                # 4. Push Updates
                layout["header"].update(header)
                layout["stats"].update(stats_panel)
                layout["graph"].update(graph_panel)
                layout["footer"].update(footer_panel)
                
            except Exception as e:
                # Show error in footer if something explodes
                layout["footer"].update(Panel(f"[red]Error: {e}[/red]", title="Status"))
            
            time.sleep(1)

if __name__ == "__main__":
    main()
