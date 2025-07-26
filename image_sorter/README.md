# Image Sorter for ClickUp Images

A fast, keyboard-driven interface for sorting thousands of images into "mockup" and "other" categories.

## Features

- **Lightning Fast**: Optimized for processing thousands of images quickly
- **Keyboard Shortcuts**: No mouse required - pure keyboard navigation
- **Resume Capability**: Automatically saves progress and resumes where you left off
- **Smart Thumbnails**: Shows optimized thumbnails by default, full-size on demand
- **Progress Tracking**: Real-time progress display and statistics
- **Auto-Skip**: Automatically skips already processed images

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the sorter:
```bash
cd image_sorter
python image_sorter.py
```

## Controls

| Key | Action |
|-----|--------|
| `1` | Mark as **Mockup** |
| `2` | Mark as **Other** |
| `S` | **Skip** this image |
| `Space` | Toggle **Full Size** view |
| `Q` | **Quit** and save progress |
| `←` | Go to **Previous** image |
| `→` | Go to **Next** image |

## Output Files

- **`sorted_images.json`**: Contains categorized image paths
- **`sorting_progress.json`**: Tracks current position for resuming

## JSON Output Format

```json
{
  "mockup": [
    "/path/to/mockup1.jpg",
    "/path/to/mockup2.png"
  ],
  "other": [
    "/path/to/other1.jpg",
    "/path/to/other2.png"
  ],
  "skipped": [
    "/path/to/skipped1.jpg"
  ]
}
```

## Tips for Speed

1. **Use thumbnails**: Default view is optimized for quick decisions
2. **Keyboard only**: Keep hands on keyboard for maximum speed
3. **Use Space**: Only view full-size when thumbnail isn't clear enough
4. **Take breaks**: The app saves progress automatically - quit anytime with `Q`

## Resume Feature

The app automatically:
- Saves your progress after each categorization
- Skips already processed images when restarting
- Shows accurate progress counters
- Preserves all previous work

Perfect for sorting large image collections over multiple sessions!