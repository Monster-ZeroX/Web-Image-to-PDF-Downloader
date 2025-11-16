# Web Image to PDF Downloader

A powerful Python script that downloads images from webpages and combines them into PDF files. Supports multi-threaded downloads, Cloudflare bypass, cookie authentication, and bulk processing.

![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- **Auto-Dependency Installation** - Automatically installs missing packages on first run
- **Multi-threaded Downloads** - Fast parallel image downloading (8 concurrent threads)
- **Cloudflare Bypass** - Automatic Cloudflare protection bypass using cloudscraper
- **Cookie Authentication** - GUI file dialog for easy cookie file selection
- **Smart Image Extraction** - Supports lazy-loaded images (`data-src` and `src` attributes)
- **Bulk Download Mode** - Process multiple URLs from a text file
- **Related Chapter Detection** - Automatically finds and offers to download related chapters/parts
- **Progress Tracking** - Real-time download progress indicators
- **Clean Output** - PDFs named after page titles with proper formatting

## Installation

### Option 1: Auto-Install (Recommended)
No manual installation required! Just run the script and it will automatically install missing dependencies:

```bash
python3 image_to_pdf_downloader.py
```

### Option 2: Manual Installation
Install dependencies manually:

```bash
pip3 install -r requirements.txt
```

## Usage

### Single Download Mode

1. Run the script:
```bash
python3 image_to_pdf_downloader.py
```

2. Select mode 1 (Single download)

3. A file dialog will open for cookies (optional):
   - Click "Cancel" to skip
   - Or select your cookies file for authenticated access

4. Enter the webpage URL when prompted

5. The script will:
   - Fetch the webpage
   - Extract all images
   - Download images in parallel (8 threads)
   - Detect related chapters and offer to download them
   - Create PDFs named after page titles
   - Save PDFs in the current directory

### Bulk Download Mode

1. Create a text file with URLs (one per line):
```
https://example.com/comic/chapter-1/
https://example.com/comic/chapter-2/
https://example.com/comic/chapter-3/
```

2. Run the script and select mode 2 (Bulk download)

3. Select your URLs file in the file dialog

4. Choose download strategy:
   - Option 1: Confirm each download
   - Option 2: Auto-download all

## Cookie Export Guide

For websites requiring authentication or cookie consent:

### Chrome/Edge
1. Install [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) extension
2. Visit the website and log in
3. Click the extension icon and export cookies
4. Save the cookies.txt file

### Firefox
1. Install [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) extension
2. Visit the website and log in
3. Click the extension icon and export cookies
4. Save the cookies.txt file

## Requirements

- Python 3.7+
- requests
- beautifulsoup4
- Pillow
- reportlab
- cloudscraper (optional, for Cloudflare bypass)

## Example Output

```
============================================================
Web Image to PDF Downloader
============================================================

Opening file dialog to select cookies file...
Selected: C:\Users\YourName\Downloads\cookies.txt
✓ Loaded 15 cookies from C:\Users\YourName\Downloads\cookies.txt

============================================================
Download Mode Selection
============================================================
1. Single download (enter URLs one by one)
2. Bulk download (load URLs from text file)
3. Exit

Select mode (1/2/3): 1

Enter the webpage URL: https://example.com/comic/chapter-1/

Fetching page: https://example.com/comic/chapter-1/
Page title: Chapter 1 - Example Comic
Found 25 images
✓ Found 3 related chapters/parts

Downloading images with multi-threading...
  [1/25] ✓ Downloaded: 001.jpg
  [2/25] ✓ Downloaded: 002.jpg
  ...
  [25/25] ✓ Downloaded: 025.jpg
✓ Successfully downloaded 25/25 images

Creating PDF: Chapter_1_-_Example_Comic.pdf
✓ PDF created successfully: Chapter_1_-_Example_Comic.pdf
  Total pages: 25

⭐ Found 3 related chapters/parts. Download them all? (yes/no):
```

## Technical Details

- **Multi-threading**: 8 concurrent download threads for optimal speed
- **Image Processing**: Automatic RGB conversion for PDF compatibility
- **Format Support**: JPG, JPEG, PNG, GIF, WEBP, BMP
- **Error Handling**: Graceful handling of failed downloads with detailed logging
- **Temporary Files**: Automatic cleanup of temporary download files
- **Headers**: Browser-like headers to avoid bot detection
- **Cloudflare**: Automatic bypass using cloudscraper when available

## Project Structure

```
AAL/
├── image_to_pdf_downloader.py    # Main script
├── requirements.txt              # Python dependencies
├── README.md                     # Documentation
├── Downloads/                    # Output directory (created automatically)
└── .gitignore                    # Git ignore rules
```

## Security & Privacy

- Cookie files are excluded from version control
- No data is sent to third parties
- All processing happens locally
- Respects robots.txt and rate limiting

## Troubleshooting

### Script can't find images
- Try different websites - some use dynamic JavaScript loading
- Check if cookies are needed for access

### Downloads are slow
- The script uses 8 concurrent threads by default
- Some servers may rate-limit requests

### Cloudflare errors
- Make sure cloudscraper is installed: `pip install cloudscraper`
- Try exporting fresh cookies from your browser

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational purposes and personal use only. Please respect website terms of service and copyright laws. Only download content you have permission to access.

## Author

Created for personal use and shared with the community.

## Acknowledgments

- Uses [cloudscraper](https://github.com/VeNoMouS/cloudscraper) for Cloudflare bypass
- Built with [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) for HTML parsing
- PDF generation powered by [Pillow](https://python-pillow.org/) and [ReportLab](https://www.reportlab.com/)
