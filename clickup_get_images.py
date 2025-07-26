"""
ClickUp Image Downloader
Downloads all image attachments from a ClickUp Workspace with resume capability.

Requires: requests, python-dotenv, rich
Usage: python clickup_get_images.py
"""

import os, time, requests, pathlib, math, json, hashlib
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn, MofNCompleteColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

load_dotenv()
TOKEN = os.getenv("CLICKUP_TOKEN")
TEAM  = os.getenv("TEAM_ID")
HEAD  = {"Authorization": TOKEN}
BASE  = "https://api.clickup.com/api/v2"
OUT_DIR = pathlib.Path("images_download")
METADATA_FILE = OUT_DIR / ".download_metadata.json"
FAILED_DOWNLOADS_FILE = OUT_DIR / ".failed_downloads.json"
PROCESSED_TASKS_FILE = OUT_DIR / ".processed_tasks.json"
console = Console()
RATE_DELAY = 0.6           # seconds between requests (≈85 req/min)

def load_metadata():
    if METADATA_FILE.exists():
        try:
            with open(METADATA_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_metadata(metadata):
    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)

def get_file_hash(file_path, chunk_size=8192):
    hash_obj = hashlib.md5()
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()

def is_duplicate(file_path, url, expected_size=None):
    if not file_path.exists():
        return False
    
    # Check file size if provided
    if expected_size and file_path.stat().st_size != expected_size:
        return False
    
    # Load metadata to check if this URL was already downloaded
    metadata = load_metadata()
    file_key = str(file_path.relative_to(OUT_DIR))
    
    if file_key in metadata:
        stored_info = metadata[file_key]
        # Check if same URL and file still exists with correct size
        if (stored_info.get('url') == url and 
            file_path.exists() and 
            stored_info.get('size') == file_path.stat().st_size):
            return True
    
    return False

def record_download(file_path, url, size):
    metadata = load_metadata()
    file_key = str(file_path.relative_to(OUT_DIR))
    metadata[file_key] = {
        'url': url,
        'size': size,
        'downloaded_at': time.time()
    }
    save_metadata(metadata)

def load_failed_downloads():
    if FAILED_DOWNLOADS_FILE.exists():
        try:
            with open(FAILED_DOWNLOADS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []

def log_failed_download(url, dest, error):
    failed_downloads = load_failed_downloads()
    failed_downloads.append({
        'url': url,
        'dest': str(dest.relative_to(OUT_DIR)),
        'error': error,
        'failed_at': time.time()
    })
    FAILED_DOWNLOADS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(FAILED_DOWNLOADS_FILE, 'w') as f:
        json.dump(failed_downloads, f, indent=2)

def load_processed_tasks():
    if PROCESSED_TASKS_FILE.exists():
        try:
            with open(PROCESSED_TASKS_FILE, 'r') as f:
                return set(json.load(f))
        except (json.JSONDecodeError, IOError):
            return set()
    return set()

def mark_task_processed(task_id):
    processed_tasks = load_processed_tasks()
    processed_tasks.add(task_id)
    PROCESSED_TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROCESSED_TASKS_FILE, 'w') as f:
        json.dump(list(processed_tasks), f, indent=2)

def api_get(url, **params):
    r = requests.get(url, headers=HEAD, params=params)
    r.raise_for_status()
    return r.json()

def get_spaces():
    data = api_get(f"{BASE}/team/{TEAM}/space")["spaces"]
    return {s["id"]: s["name"] for s in data}

def get_folder_lists(space_id):
    lists = []
    # ① folder‑less lists
    lists += api_get(f"{BASE}/space/{space_id}/list").get("lists", [])
    # ② lists inside folders
    for f in api_get(f"{BASE}/space/{space_id}/folder").get("folders", []):
        lists += f.get("lists", [])
    return lists

def iter_tasks(list_id):
    page = 0
    while True:
        data = api_get(f"{BASE}/list/{list_id}/task",
                       page=page, include_closed="true")
        yield from data.get("tasks", [])
        if data.get("last_page", True): break
        page += 1
        time.sleep(RATE_DELAY)

def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with requests.get(url, stream=True, headers=HEAD, timeout=30) as r:
            r.raise_for_status()
            content_length = r.headers.get('content-length')
            expected_size = int(content_length) if content_length else None
            
            with open(dest, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            
            # Record the download in metadata
            actual_size = dest.stat().st_size
            record_download(dest, url, actual_size)
            return True
            
    except requests.exceptions.RequestException as e:
        # Log the failed download
        log_failed_download(url, dest, str(e))
        # Clean up partial file if it exists
        if dest.exists():
            dest.unlink()
        return False

def main():
    # Create output directory
    OUT_DIR.mkdir(exist_ok=True)
    
    # Load processed tasks for resumption
    processed_tasks = load_processed_tasks()
    
    # Display header
    console.print(Panel.fit(
        "[bold blue]ClickUp Image Downloader[/bold blue]\n"
        f"Output Directory: [green]{OUT_DIR}[/green]\n"
        f"Previously processed tasks: [yellow]{len(processed_tasks)}[/yellow]",
        border_style="blue"
    ))
    
    with console.status("[bold green]Fetching spaces...") as status:
        spaces = get_spaces()
    
    console.print(f"[green]✓[/green] Found {len(spaces)} space(s)")
    
    # Count total tasks for progress tracking
    total_tasks = 0
    remaining_tasks = 0
    all_lists = []
    
    with console.status("[bold green]Counting tasks...") as status:
        for sid, sname in spaces.items():
            lists = get_folder_lists(sid)
            for lst in lists:
                tasks = list(iter_tasks(lst["id"]))
                task_count = len(tasks)
                remaining_count = len([t for t in tasks if t["id"] not in processed_tasks])
                all_lists.append((sid, sname, lst, tasks))
                total_tasks += task_count
                remaining_tasks += remaining_count
    
    console.print(f"[green]✓[/green] Found {total_tasks} total tasks ({remaining_tasks} remaining to process)")
    
    total_imgs = 0
    failed_downloads = 0
    
    # Main progress tracking
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        expand=True
    ) as progress:
        
        main_task = progress.add_task("[cyan]Processing all tasks...", total=remaining_tasks)
        
        for sid, sname, lst, tasks in all_lists:
            lname = lst["name"]
            remaining_list_tasks = [t for t in tasks if t["id"] not in processed_tasks]
            
            if not remaining_list_tasks:
                continue
                
            list_task = progress.add_task(f"[yellow]{sname}/{lname}", total=len(remaining_list_tasks))
            
            task_counter = 0
            for task in remaining_list_tasks:
                task_counter += 1
                progress.update(list_task, advance=1, description=f"[yellow]{sname}/{lname} - Task {task_counter}/{len(remaining_list_tasks)}")
                progress.update(main_task, advance=1)
                
                try:
                    tdata = api_get(f"{BASE}/task/{task['id']}")
                    
                    for att in tdata.get("attachments", []):
                        if att.get("mimetype", "").startswith("image/"):
                            fname = att.get("title") or att.get("filename")
                            path = OUT_DIR / sname / lname / fname
                            
                            # Check for duplicates using improved method
                            if not is_duplicate(path, att["url"]):
                                console.print(f"[dim]  Downloading: {fname}[/dim]")
                                success = download(att["url"], path)
                                if success:
                                    total_imgs += 1
                                else:
                                    failed_downloads += 1
                                    console.print(f"[red]  Failed to download: {fname}[/red]")
                                time.sleep(RATE_DELAY)
                            else:
                                console.print(f"[dim]  Skipping duplicate: {fname}[/dim]")
                    
                    # Mark task as processed
                    mark_task_processed(task["id"])
                    
                except Exception as e:
                    console.print(f"[red]  Error processing task {task['id']}: {str(e)}[/red]")
                    continue
                
                time.sleep(RATE_DELAY)
            
            progress.remove_task(list_task)
    
    # Final summary
    summary_text = f"[bold green]✓ Complete![/bold green]\n"
    summary_text += f"Downloaded [bold cyan]{total_imgs}[/bold cyan] images\n"
    if failed_downloads > 0:
        summary_text += f"Failed downloads: [bold red]{failed_downloads}[/bold red] (see .failed_downloads.json)\n"
    summary_text += f"Saved to: [green]{OUT_DIR.absolute()}[/green]"
    
    console.print(Panel.fit(summary_text, border_style="green"))

if __name__ == "__main__":
    main()
