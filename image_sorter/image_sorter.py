"""
Fast Image Sorter for ClickUp Images
Sorts images into "mockup" or "other" categories using keyboard shortcuts.

Controls:
- 1: Mark as mockup
- 2: Mark as other
- s: Skip this image
- q: Quit and save progress
- Space: Show full size image (if currently showing thumbnail)

Usage: python image_sorter.py
"""

import os
import json
import time
from pathlib import Path
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import messagebox
import threading

class ImageSorter:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Image Sorter - ClickUp Images")
        self.root.geometry("1200x800")
        self.root.configure(bg='black')
        
        # Paths
        self.images_dir = Path("../images_download")
        self.output_file = Path("sorted_images.json")
        self.progress_file = Path("sorting_progress.json")
        
        # Data
        self.image_paths = []
        self.current_index = 0
        self.sorted_data = self.load_sorted_data()
        self.current_image = None
        self.showing_full_size = False
        
        # UI elements
        self.image_label = None
        self.info_label = None
        self.progress_label = None
        
        self.setup_ui()
        self.load_images()
        self.load_progress()
        self.show_current_image()
        
        # Bind keyboard events
        self.root.bind('<Key>', self.handle_keypress)
        self.root.focus_set()
        
    def setup_ui(self):
        # Main frame
        main_frame = tk.Frame(self.root, bg='black')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Info frame at top
        info_frame = tk.Frame(main_frame, bg='black')
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Progress label
        self.progress_label = tk.Label(info_frame, text="Loading...", 
                                     font=('Arial', 14, 'bold'), 
                                     bg='black', fg='white')
        self.progress_label.pack(side=tk.LEFT)
        
        # Controls info
        controls_text = "Controls: [1] Mockup  [2] Other  [S] Skip  [Space] Full Size  [Q] Quit"
        controls_label = tk.Label(info_frame, text=controls_text, 
                                font=('Arial', 12), 
                                bg='black', fg='cyan')
        controls_label.pack(side=tk.RIGHT)
        
        # Image frame
        image_frame = tk.Frame(main_frame, bg='black', relief=tk.SUNKEN, bd=2)
        image_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Image label
        self.image_label = tk.Label(image_frame, bg='black', text="Loading images...")
        self.image_label.pack(expand=True)
        
        # File info frame
        self.info_label = tk.Label(main_frame, text="", 
                                 font=('Arial', 11), 
                                 bg='black', fg='yellow', 
                                 wraplength=1000, justify=tk.LEFT)
        self.info_label.pack(fill=tk.X)
        
    def load_images(self):
        """Load all image paths from the images_download directory"""
        self.image_paths = []
        
        if not self.images_dir.exists():
            messagebox.showerror("Error", f"Images directory not found: {self.images_dir}")
            return
            
        # Supported image extensions
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.jfif'}
        
        # Walk through all subdirectories
        for root, dirs, files in os.walk(self.images_dir):
            for file in files:
                if Path(file).suffix.lower() in image_extensions:
                    full_path = Path(root) / file
                    self.image_paths.append(full_path)
        
        self.image_paths.sort()  # Sort for consistent ordering
        print(f"Found {len(self.image_paths)} images")
        
    def load_sorted_data(self):
        """Load existing sorted data"""
        if self.output_file.exists():
            try:
                with open(self.output_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {"mockup": [], "other": [], "skipped": []}
        return {"mockup": [], "other": [], "skipped": []}
    
    def save_sorted_data(self):
        """Save sorted data to JSON"""
        with open(self.output_file, 'w') as f:
            json.dump(self.sorted_data, f, indent=2)
            
    def load_progress(self):
        """Load progress from previous session"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    data = json.load(f)
                    self.current_index = data.get('current_index', 0)
            except (json.JSONDecodeError, IOError):
                self.current_index = 0
                
        # Skip already processed images
        while (self.current_index < len(self.image_paths) and 
               self.is_already_processed(self.image_paths[self.current_index])):
            self.current_index += 1
    
    def save_progress(self):
        """Save current progress"""
        with open(self.progress_file, 'w') as f:
            json.dump({'current_index': self.current_index}, f)
    
    def is_already_processed(self, image_path):
        """Check if image is already processed"""
        path_str = str(image_path)
        return (path_str in self.sorted_data.get("mockup", []) or 
                path_str in self.sorted_data.get("other", []) or 
                path_str in self.sorted_data.get("skipped", []))
    
    def show_current_image(self):
        """Display current image"""
        if self.current_index >= len(self.image_paths):
            self.show_completion()
            return
            
        image_path = self.image_paths[self.current_index]
        
        # Update progress
        processed_count = len(self.sorted_data["mockup"]) + len(self.sorted_data["other"])
        progress_text = f"Image {self.current_index + 1}/{len(self.image_paths)} | Processed: {processed_count} | Mockups: {len(self.sorted_data['mockup'])} | Others: {len(self.sorted_data['other'])}"
        self.progress_label.config(text=progress_text)
        
        # Update file info
        relative_path = image_path.relative_to(self.images_dir)
        info_text = f"File: {relative_path}\nPath: {image_path}"
        self.info_label.config(text=info_text)
        
        # Load and display image
        try:
            with Image.open(image_path) as img:
                # Get image info
                width, height = img.size
                info_text += f"\nSize: {width}x{height}"
                self.info_label.config(text=info_text)
                
                # Resize for display (thumbnail by default)
                if not self.showing_full_size:
                    display_size = self.calculate_thumbnail_size(width, height, 800, 600)
                else:
                    # Full size but fit in window
                    display_size = self.calculate_thumbnail_size(width, height, 1100, 700)
                
                img_resized = img.resize(display_size, Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img_resized)
                
                self.image_label.config(image=photo, text="")
                self.image_label.image = photo  # Keep a reference
                
        except Exception as e:
            self.image_label.config(image="", text=f"Error loading image: {str(e)}")
            self.image_label.image = None
    
    def calculate_thumbnail_size(self, img_width, img_height, max_width, max_height):
        """Calculate thumbnail size maintaining aspect ratio"""
        ratio = min(max_width / img_width, max_height / img_height)
        return (int(img_width * ratio), int(img_height * ratio))
    
    def handle_keypress(self, event):
        """Handle keyboard input"""
        key = event.keysym.lower()
        
        if key == '1':
            self.categorize_image("mockup")
        elif key == '2':
            self.categorize_image("other")
        elif key == 's':
            self.categorize_image("skipped")
        elif key == 'space':
            self.toggle_full_size()
        elif key == 'q':
            self.quit_application()
        elif key in ['right', 'return']:  # Alternative next keys
            self.next_image()
        elif key == 'left':  # Go back
            self.previous_image()
    
    def categorize_image(self, category):
        """Categorize current image and move to next"""
        if self.current_index >= len(self.image_paths):
            return
            
        image_path = str(self.image_paths[self.current_index])
        
        # Remove from other categories if exists
        for cat in ["mockup", "other", "skipped"]:
            if image_path in self.sorted_data[cat]:
                self.sorted_data[cat].remove(image_path)
        
        # Add to new category
        self.sorted_data[category].append(image_path)
        
        # Save data and progress
        self.save_sorted_data()
        self.save_progress()
        
        # Move to next image
        self.next_image()
    
    def next_image(self):
        """Move to next unprocessed image"""
        self.current_index += 1
        self.showing_full_size = False
        
        # Skip already processed images
        while (self.current_index < len(self.image_paths) and 
               self.is_already_processed(self.image_paths[self.current_index])):
            self.current_index += 1
            
        self.show_current_image()
    
    def previous_image(self):
        """Move to previous image"""
        if self.current_index > 0:
            self.current_index -= 1
            self.showing_full_size = False
            self.show_current_image()
    
    def toggle_full_size(self):
        """Toggle between thumbnail and full size view"""
        self.showing_full_size = not self.showing_full_size
        self.show_current_image()
    
    def show_completion(self):
        """Show completion message"""
        processed_count = len(self.sorted_data["mockup"]) + len(self.sorted_data["other"])
        completion_text = f"""
        🎉 SORTING COMPLETE! 🎉
        
        Total processed: {processed_count}
        Mockups: {len(self.sorted_data['mockup'])}
        Others: {len(self.sorted_data['other'])}
        Skipped: {len(self.sorted_data['skipped'])}
        
        Results saved to: {self.output_file}
        """
        
        self.image_label.config(image="", text=completion_text, fg='green', font=('Arial', 16, 'bold'))
        self.image_label.image = None
        
        self.progress_label.config(text="✅ COMPLETED", fg='green')
    
    def quit_application(self):
        """Quit and save progress"""
        self.save_sorted_data()
        self.save_progress()
        
        processed_count = len(self.sorted_data["mockup"]) + len(self.sorted_data["other"])
        messagebox.showinfo("Progress Saved", 
                          f"Progress saved!\nProcessed: {processed_count} images\nYou can resume anytime by running the script again.")
        self.root.quit()
    
    def run(self):
        """Start the application"""
        self.root.protocol("WM_DELETE_WINDOW", self.quit_application)
        self.root.mainloop()

if __name__ == "__main__":
    try:
        sorter = ImageSorter()
        sorter.run()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        messagebox.showerror("Error", f"An error occurred: {e}")