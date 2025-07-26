"""
Copy Sorted Images Script
Copies images from sorted_images.json into organized folders based on their categories.

This script reads the sorted_images.json file and copies all categorized images
into /home/roman/pomp_cheer_scraper_clickup/sorted_images/mockup and 
/home/roman/pomp_cheer_scraper_clickup/sorted_images/other folders.

Usage: python copy_sorted_images.py
"""

import json
import shutil
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn, MofNCompleteColumn
from rich.panel import Panel
from rich.table import Table
import os

console = Console()

def load_sorted_data():
    """Load the sorted images JSON file"""
    json_file = Path("sorted_images.json")
    if not json_file.exists():
        console.print(f"[red]Error: {json_file} not found![/red]")
        console.print("Please run the image sorter first to generate the sorted data.")
        return None
    
    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        console.print(f"[red]Error reading {json_file}: {e}[/red]")
        return None

def create_destination_folders():
    """Create the destination folder structure"""
    base_dir = Path("/home/roman/pomp_cheer_scraper_clickup/sorted_images")
    mockup_dir = base_dir / "mockup"
    other_dir = base_dir / "other"
    
    # Create directories
    mockup_dir.mkdir(parents=True, exist_ok=True)
    other_dir.mkdir(parents=True, exist_ok=True)
    
    console.print(f"[green]✓[/green] Created destination directories:")
    console.print(f"  - {mockup_dir}")
    console.print(f"  - {other_dir}")
    
    return mockup_dir, other_dir

def get_unique_filename(dest_dir, filename):
    """Generate a unique filename if a file with the same name already exists"""
    dest_path = dest_dir / filename
    if not dest_path.exists():
        return dest_path
    
    # File exists, create unique name
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    
    while True:
        new_name = f"{stem}_{counter:03d}{suffix}"
        new_path = dest_dir / new_name
        if not new_path.exists():
            return new_path
        counter += 1

def copy_images(sorted_data, mockup_dir, other_dir):
    """Copy images to their respective folders with progress tracking"""
    
    # Count total images to copy
    total_mockups = len(sorted_data.get("mockup", []))
    total_others = len(sorted_data.get("other", []))
    total_images = total_mockups + total_others
    
    if total_images == 0:
        console.print("[yellow]No images to copy![/yellow]")
        return
    
    # Statistics
    copied_count = 0
    skipped_count = 0
    error_count = 0
    errors = []
    
    console.print(f"\n[cyan]Starting copy operation...[/cyan]")
    console.print(f"Mockups to copy: [bold cyan]{total_mockups}[/bold cyan]")
    console.print(f"Others to copy: [bold cyan]{total_others}[/bold cyan]")
    console.print(f"Total: [bold cyan]{total_images}[/bold cyan] images\n")
    
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
        
        main_task = progress.add_task("[cyan]Copying all images...", total=total_images)
        
        # Copy mockups
        if total_mockups > 0:
            mockup_task = progress.add_task("[yellow]Copying mockups...", total=total_mockups)
            
            for i, image_path in enumerate(sorted_data.get("mockup", [])):
                source_path = Path(image_path)
                
                progress.update(mockup_task, advance=1, 
                              description=f"[yellow]Copying mockups... {source_path.name}")
                progress.update(main_task, advance=1)
                
                try:
                    if not source_path.exists():
                        console.print(f"[dim red]  Missing: {source_path}[/dim red]")
                        skipped_count += 1
                        continue
                    
                    # Get unique destination path
                    dest_path = get_unique_filename(mockup_dir, source_path.name)
                    
                    # Copy file
                    shutil.copy2(source_path, dest_path)
                    copied_count += 1
                    
                    if dest_path.name != source_path.name:
                        console.print(f"[dim yellow]  Renamed: {source_path.name} → {dest_path.name}[/dim yellow]")
                    
                except Exception as e:
                    error_count += 1
                    error_msg = f"Error copying {source_path}: {str(e)}"
                    errors.append(error_msg)
                    console.print(f"[dim red]  {error_msg}[/dim red]")
            
            progress.remove_task(mockup_task)
        
        # Copy others
        if total_others > 0:
            other_task = progress.add_task("[green]Copying others...", total=total_others)
            
            for i, image_path in enumerate(sorted_data.get("other", [])):
                source_path = Path(image_path)
                
                progress.update(other_task, advance=1, 
                              description=f"[green]Copying others... {source_path.name}")
                progress.update(main_task, advance=1)
                
                try:
                    if not source_path.exists():
                        console.print(f"[dim red]  Missing: {source_path}[/dim red]")
                        skipped_count += 1
                        continue
                    
                    # Get unique destination path
                    dest_path = get_unique_filename(other_dir, source_path.name)
                    
                    # Copy file
                    shutil.copy2(source_path, dest_path)
                    copied_count += 1
                    
                    if dest_path.name != source_path.name:
                        console.print(f"[dim yellow]  Renamed: {source_path.name} → {dest_path.name}[/dim yellow]")
                    
                except Exception as e:
                    error_count += 1
                    error_msg = f"Error copying {source_path}: {str(e)}"
                    errors.append(error_msg)
                    console.print(f"[dim red]  {error_msg}[/dim red]")
            
            progress.remove_task(other_task)
    
    return copied_count, skipped_count, error_count, errors

def show_summary(copied_count, skipped_count, error_count, errors, mockup_dir, other_dir):
    """Display final summary"""
    
    # Count files in destination folders
    mockup_files = len([f for f in mockup_dir.iterdir() if f.is_file()])
    other_files = len([f for f in other_dir.iterdir() if f.is_file()])
    
    # Create summary table
    table = Table(title="Copy Operation Summary", style="cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Count", justify="right", style="green")
    
    table.add_row("Successfully Copied", str(copied_count))
    table.add_row("Errors", str(error_count), style="red" if error_count > 0 else "green")
    table.add_row("Missing Files", str(skipped_count), style="yellow" if skipped_count > 0 else "green")
    table.add_row("", "")  # Empty row as separator
    table.add_row("Mockup Images", str(mockup_files), style="yellow")
    table.add_row("Other Images", str(other_files), style="green")
    table.add_row("Total Organized", str(mockup_files + other_files), style="bold cyan")
    
    console.print("\n")
    console.print(table)
    
    # Show folder locations
    console.print(f"\n[bold green]✓ Images organized into:[/bold green]")
    console.print(f"  📁 Mockups: [cyan]{mockup_dir}[/cyan] ({mockup_files} files)")
    console.print(f"  📁 Others:  [cyan]{other_dir}[/cyan] ({other_files} files)")
    
    # Show errors if any
    if errors:
        console.print(f"\n[bold red]Errors encountered:[/bold red]")
        for error in errors[:10]:  # Show first 10 errors
            console.print(f"  [dim red]• {error}[/dim red]")
        if len(errors) > 10:
            console.print(f"  [dim red]... and {len(errors) - 10} more errors[/dim red]")

def main():
    """Main function"""
    console.print(Panel.fit(
        "[bold blue]Image Copy Script[/bold blue]\n"
        "Copies sorted images into organized folders",
        border_style="blue"
    ))
    
    # Load sorted data
    console.print("\n[cyan]Loading sorted image data...[/cyan]")
    sorted_data = load_sorted_data()
    if not sorted_data:
        return
    
    # Show what we found
    mockup_count = len(sorted_data.get("mockup", []))
    other_count = len(sorted_data.get("other", []))
    skipped_count = len(sorted_data.get("skipped", []))
    
    console.print(f"[green]✓[/green] Found sorted data:")
    console.print(f"  - Mockups: {mockup_count}")
    console.print(f"  - Others: {other_count}")
    console.print(f"  - Skipped: {skipped_count} (will not be copied)")
    
    if mockup_count == 0 and other_count == 0:
        console.print("[yellow]No images to copy! Please sort some images first.[/yellow]")
        return
    
    # Create destination folders
    console.print(f"\n[cyan]Creating destination folders...[/cyan]")
    mockup_dir, other_dir = create_destination_folders()
    
    # Confirm operation
    console.print(f"\n[bold yellow]Ready to copy {mockup_count + other_count} images.[/bold yellow]")
    response = input("Continue? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        console.print("[yellow]Operation cancelled.[/yellow]")
        return
    
    # Copy images
    copied_count, skipped_count, error_count, errors = copy_images(sorted_data, mockup_dir, other_dir)
    
    # Show summary
    show_summary(copied_count, skipped_count, error_count, errors, mockup_dir, other_dir)
    
    console.print(f"\n[bold green]🎉 Copy operation complete![/bold green]")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")