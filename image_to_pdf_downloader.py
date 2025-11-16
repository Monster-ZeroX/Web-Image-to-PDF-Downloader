#!/usr/bin/env python3
"""
Web Image to PDF Downloader
Downloads images from a webpage and combines them into a PDF file.
"""

import os
import re
import sys
import subprocess
import importlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Auto-install missing packages
def install_and_import(package_name, import_name=None):
    """Install package if not available and import it."""
    if import_name is None:
        import_name = package_name

    try:
        return importlib.import_module(import_name)
    except ImportError:
        print(f"📦 Installing {package_name}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name, "--quiet"])
            print(f"✓ {package_name} installed successfully")
            return importlib.import_module(import_name)
        except Exception as e:
            print(f"✗ Failed to install {package_name}: {e}")
            sys.exit(1)

# Install and import required packages
requests = install_and_import("requests")
bs4 = install_and_import("beautifulsoup4", "bs4")
BeautifulSoup = bs4.BeautifulSoup
PIL = install_and_import("Pillow", "PIL")
from PIL import Image
reportlab = install_and_import("reportlab")
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Try to import cloudscraper for Cloudflare bypass
try:
    cloudscraper = install_and_import("cloudscraper")
    HAS_CLOUDSCRAPER = True
except:
    HAS_CLOUDSCRAPER = False
    print("⚠ cloudscraper not available, will try standard requests")

# Standard library imports
from pathlib import Path
from io import BytesIO
import tempfile
import time
import tkinter as tk
from tkinter import filedialog


class ImageToPDFDownloader:
    def __init__(self, url, cookies_file=None):
        self.url = url
        self.cookies_file = cookies_file

        # Use cloudscraper if available for Cloudflare bypass, otherwise use requests
        if HAS_CLOUDSCRAPER:
            print("✓ Using cloudscraper for Cloudflare bypass")
            self.session = cloudscraper.create_scraper()
        else:
            self.session = requests.Session()

        self.images = []
        self.temp_dir = tempfile.mkdtemp()

        # Set a realistic user agent and other headers to mimic a browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': self.url
        })

        # Load cookies if provided
        if cookies_file and os.path.exists(cookies_file):
            self.load_cookies(cookies_file)

    def load_cookies(self, cookies_file):
        """Load cookies from Netscape format cookie file."""
        try:
            cookies_loaded = 0
            with open(cookies_file, 'r') as f:
                for line in f:
                    if not line.strip() or line.startswith('#'):
                        continue

                    parts = line.strip().split('\t')
                    if len(parts) >= 7:
                        domain, _, path, secure, _, name, value = parts[:7]
                        self.session.cookies.set(name, value, domain=domain, path=path)
                        cookies_loaded += 1
            print(f"✓ Loaded {cookies_loaded} cookies from {cookies_file}")
        except Exception as e:
            print(f"⚠ Warning: Could not load cookies: {e}")

    def fetch_page(self):
        """Fetch the webpage content."""
        try:
            print(f"Fetching page: {self.url}")
            print(f"\n📋 Debug Info:")
            print(f"  Total cookies loaded: {len(self.session.cookies)}")

            # Add more complete headers for each request
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
                'Cache-Control': 'max-age=0',
                'Referer': self.url,
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            }

            print(f"  Headers being sent:")
            for key, value in headers.items():
                if len(str(value)) > 60:
                    print(f"    {key}: {str(value)[:60]}...")
                else:
                    print(f"    {key}: {value}")

            # Show some cookies
            if self.session.cookies:
                print(f"  Sample cookies:")
                for i, cookie in enumerate(self.session.cookies):
                    if i < 3:
                        print(f"    {cookie.name}={cookie.value[:20]}...")
                    if i >= 3:
                        break

            response = self.session.get(self.url, headers=headers, timeout=30, allow_redirects=True, verify=True)

            print(f"\n📊 Response Info:")
            print(f"  Status Code: {response.status_code}")
            print(f"  Content Type: {response.headers.get('Content-Type', 'N/A')}")
            print(f"  Content Length: {len(response.text)} bytes")
            print(f"  Response Headers:")
            for key, value in response.headers.items():
                if key.lower() in ['server', 'set-cookie', 'content-type', 'content-length']:
                    print(f"    {key}: {value[:100] if len(str(value)) > 100 else value}")

            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"\n✗ Error fetching page: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def extract_images(self, html_content):
        """Extract image URLs from HTML content with multiple strategies."""
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract page title
        title_tag = soup.find('title')
        self.page_title = title_tag.text.strip() if title_tag else "Downloaded_Images"

        # Clean title for filename
        self.page_title = re.sub(r'[<>:"/\\|?*]', '_', self.page_title)

        print(f"Page title: {self.page_title}")

        # Check if this is a paginated gallery (one image per page)
        if self.is_paginated_gallery(html_content):
            print("🔍 Detected paginated gallery (one image per page)")
            return self.extract_paginated_images(html_content)

        image_urls = []

        # Strategy 1: Check for noscript tags (common for JavaScript galleries)
        noscript_tags = soup.find_all('noscript')
        for noscript in noscript_tags:
            noscript_soup = BeautifulSoup(str(noscript), 'html.parser')
            noscript_imgs = noscript_soup.find_all('img', {'src': True})
            for img in noscript_imgs:
                src = img.get('src')
                if src and self.is_image_url(src.strip()):
                    image_urls.append(src.strip())

        # Strategy 2: Find all img tags with data-src attribute
        if not image_urls:
            img_tags = soup.find_all('img', {'data-src': True})
            for img in img_tags:
                src = img.get('data-src')
                if src and self.is_image_url(src.strip()):
                    image_urls.append(src.strip())

        # Strategy 3: Fallback to regular src attribute
        if not image_urls:
            img_tags = soup.find_all('img', {'src': True})
            for img in img_tags:
                src = img.get('src')
                if src and self.is_image_url(src.strip()):
                    image_urls.append(src.strip())

        # Clean URLs to get full-size images
        image_urls = [self.clean_image_url(url) for url in image_urls]

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in image_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        image_urls = unique_urls

        # Smart sort: Try to maintain numerical order
        image_urls = self.smart_sort_images(image_urls)

        print(f"Found {len(image_urls)} images")
        return image_urls

    def is_paginated_gallery(self, html_content):
        """Detect if this is a paginated gallery (one image per page with Next/Previous buttons)."""
        soup = BeautifulSoup(html_content, 'html.parser')

        # Look for pagination indicators
        pagination_indicators = [
            'Next Image',
            'Previous Image',
            'pagGaleria',
            'next-page',
            'prev-page',
        ]

        text_content = html_content.lower()
        for indicator in pagination_indicators:
            if indicator.lower() in text_content:
                return True

        # Look for navigation controls
        nav_divs = soup.find_all('div', {'id': re.compile(r'control', re.I)})
        if nav_divs:
            return True

        return False

    def extract_paginated_images(self, html_content):
        """Extract images from paginated gallery by crawling through all pages."""
        print("📖 Crawling paginated gallery...")

        all_image_urls = []
        visited_urls = set()
        current_url = self.url

        # Parse the initial page structure to understand the URL pattern
        base_pattern = self.detect_url_pattern(current_url)

        page_number = 1
        max_pages = 200  # Safety limit

        while page_number <= max_pages and current_url and current_url not in visited_urls:
            print(f"\n  📄 Page {page_number}: {current_url}")
            visited_urls.add(current_url)

            try:
                # Fetch the page
                if current_url == self.url:
                    # Use already fetched content for first page
                    page_html = html_content
                else:
                    response = self.session.get(current_url, timeout=30)
                    response.raise_for_status()
                    page_html = response.text

                soup = BeautifulSoup(page_html, 'html.parser')

                # Extract the main image from this page
                image_url = self.extract_main_image(soup)
                if image_url:
                    all_image_urls.append(image_url)
                    print(f"    ✓ Found image: {image_url.split('/')[-1][:50]}")
                else:
                    print(f"    ⚠ No image found on this page")

                # Find the "Next" link
                next_url = self.find_next_page_url(soup, current_url)

                if not next_url or next_url in visited_urls:
                    print(f"\n✓ Reached end of gallery at page {page_number}")
                    break

                current_url = next_url
                page_number += 1

                # Small delay to be respectful
                time.sleep(0.3)

            except Exception as e:
                print(f"    ✗ Error on page {page_number}: {e}")
                break

        print(f"\n📊 Total pages crawled: {page_number}")
        print(f"📊 Total images found: {len(all_image_urls)}")

        return all_image_urls

    def detect_url_pattern(self, url):
        """Detect the URL pattern for pagination."""
        # Extract base URL without the page number
        # Example: /comic/chapter-01/ or /comic/chapter-01-page-5/
        match = re.search(r'(.*?)(-\d+)?/?$', url)
        if match:
            return match.group(1)
        return url

    def extract_main_image(self, soup):
        """Extract the main/primary image from a single page."""
        # Try multiple strategies to find the main image

        # Strategy 1: Look for images in main content area
        main_content = soup.find(['div', 'article'], {'id': re.compile(r'content|main|comic|image', re.I)})
        if main_content:
            img = main_content.find('img', {'src': True})
            if img and self.is_image_url(img.get('src', '').strip()):
                return self.clean_image_url(img.get('src').strip())

        # Strategy 2: Look for images with specific classes
        img = soup.find('img', {'class': re.compile(r'main|comic|content|gallery|primary', re.I), 'src': True})
        if img and self.is_image_url(img.get('src', '').strip()):
            return self.clean_image_url(img.get('src').strip())

        # Strategy 3: Find the largest image (likely the main content)
        all_imgs = soup.find_all('img', {'src': True})
        candidate_images = []

        for img in all_imgs:
            src = img.get('src', '').strip()
            if not src or not self.is_image_url(src):
                continue

            # Skip common UI elements
            if any(skip in src.lower() for skip in ['logo', 'icon', 'avatar', 'button', 'banner', 'ad', 'thumb']):
                continue

            # Check for size hints in attributes
            width = img.get('width', '')
            height = img.get('height', '')

            try:
                size_score = 0
                if width and width.isdigit():
                    size_score += int(width)
                if height and height.isdigit():
                    size_score += int(height)

                candidate_images.append((size_score, src))
            except:
                candidate_images.append((0, src))

        if candidate_images:
            # Sort by size score and return the largest
            candidate_images.sort(key=lambda x: x[0], reverse=True)
            return self.clean_image_url(candidate_images[0][1])

        return None

    def find_next_page_url(self, soup, current_url):
        """Find the URL of the next page in pagination."""
        # Strategy 1: Look for links with "Next" text
        next_keywords = ['next image', 'next page', 'next >>', '>>']

        for keyword in next_keywords:
            links = soup.find_all('a', string=re.compile(keyword, re.I))
            for link in links:
                href = link.get('href')
                if href:
                    return self.normalize_url(href, current_url)

        # Strategy 2: Look for links inside elements with "next" classes
        next_elements = soup.find_all(['a', 'span'], {'class': re.compile(r'next|pagGaleria', re.I)})
        for elem in next_elements:
            if elem.name == 'a':
                href = elem.get('href')
                if href:
                    return self.normalize_url(href, current_url)
            else:
                # Check parent
                parent = elem.find_parent('a')
                if parent:
                    href = parent.get('href')
                    if href:
                        return self.normalize_url(href, current_url)

        # Strategy 3: Look for numbered pagination (increment current page number)
        match = re.search(r'(.*?)[-/](\d+)/?$', current_url)
        if match:
            base_url = match.group(1)
            current_page = int(match.group(2))
            next_page = current_page + 1

            # Try to verify if next page exists by looking for it in the HTML
            potential_next = f"{base_url}-{next_page:02d}/" if current_page < 10 else f"{base_url}-{next_page}/"
            if potential_next in soup.get_text() or any(potential_next in str(a) for a in soup.find_all('a')):
                return potential_next

        return None

    def normalize_url(self, href, current_url):
        """Convert relative URL to absolute URL."""
        if href.startswith('http://') or href.startswith('https://'):
            return href

        # Parse current URL to get base
        from urllib.parse import urljoin
        return urljoin(current_url, href)

    def detect_related_chapters(self, html_content):
        """Detect related chapters/parts of the same story from select dropdown."""
        soup = BeautifulSoup(html_content, 'html.parser')

        # Look for chapter select dropdown
        select_elem = soup.find('select', {'class': 'single-chapter-select'})

        if not select_elem:
            print("No related chapters found")
            return []

        # Extract all option elements
        options = select_elem.find_all('option')

        if not options:
            print("No related chapters found")
            return []

        # Extract URLs from data-redirect attribute
        related_chapters = []
        for option in options:
            redirect_url = option.get('data-redirect')
            chapter_name = option.text.strip()

            if redirect_url and chapter_name:
                # Check if this is the same story (extract story ID from current URL)
                if self.is_same_story(redirect_url):
                    related_chapters.append({
                        'url': redirect_url,
                        'name': chapter_name
                    })

        print(f"✓ Found {len(related_chapters)} related chapters/parts")
        return related_chapters

    def is_same_story(self, url):
        """Check if a URL belongs to the same story."""
        # Extract story ID from both URLs
        current_story = self.extract_story_id(self.url)
        new_story = self.extract_story_id(url)

        return current_story == new_story

    def extract_story_id(self, url):
        """Extract story identifier from URL."""
        # Pattern: /porncomic/story-name/chapter/
        # We want the 'story-name' part
        try:
            parts = url.split('/porncomic/')
            if len(parts) > 1:
                story_part = parts[1].split('/')[0]
                return story_part
        except:
            pass
        return None

    def is_image_url(self, url):
        """Check if URL points to an image."""
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')
        return any(url.lower().endswith(ext) for ext in image_extensions)

    def clean_image_url(self, url):
        """Clean image URL to get full-size version."""
        # Remove common image resizing paths
        # Example: /styles/juicebox_medium/public/ -> /
        url = re.sub(r'/styles/[^/]+/public/', '/', url)

        # Remove query parameters that might cause issues (keep the base URL)
        # But preserve the essential parts like itok for authentication
        if '?' in url:
            base_url = url.split('?')[0]
            # Check if there's an itok parameter (image token for Drupal sites)
            itok_match = re.search(r'[?&]itok=([^&]+)', url)
            if itok_match:
                url = f"{base_url}?itok={itok_match.group(1)}"
            else:
                url = base_url

        return url

    def extract_number_from_filename(self, url):
        """Extract number from filename for sorting."""
        # Get the filename from URL
        filename = url.split('/')[-1].split('?')[0]

        # Try to find numbers in the filename
        # Pattern 1: Leading numbers like "01_", "001_", "1_"
        match = re.search(r'^(\d+)[\W_]', filename)
        if match:
            return int(match.group(1))

        # Pattern 2: Numbers after underscore like "_01.", "_001.", "_1."
        match = re.search(r'[\W_](\d+)\.', filename)
        if match:
            return int(match.group(1))

        # Pattern 3: Any number in the filename
        match = re.search(r'(\d+)', filename)
        if match:
            return int(match.group(1))

        # No number found
        return float('inf')

    def smart_sort_images(self, image_urls):
        """Sort images intelligently based on numbers in filenames."""
        if not image_urls:
            return image_urls

        # Check if URLs contain numbers that suggest ordering
        urls_with_numbers = []
        for url in image_urls:
            number = self.extract_number_from_filename(url)
            urls_with_numbers.append((number, url))

        # Sort by extracted number
        urls_with_numbers.sort(key=lambda x: x[0])

        # Extract sorted URLs
        sorted_urls = [url for _, url in urls_with_numbers]

        # Debug: Show sorting
        print(f"📊 Image ordering detected:")
        for idx, (num, url) in enumerate(urls_with_numbers[:5], 1):
            filename = url.split('/')[-1].split('?')[0]
            if num != float('inf'):
                print(f"  [{idx}] Number: {num:3d} - {filename[:50]}...")
            else:
                print(f"  [{idx}] No number - {filename[:50]}...")
        if len(urls_with_numbers) > 5:
            print(f"  ... and {len(urls_with_numbers) - 5} more images")

        return sorted_urls

    def download_images(self, image_urls):
        """Download all images using multi-threading for speed."""
        print("\nDownloading images with multi-threading...")
        downloaded_files = [None] * len(image_urls)  # Pre-allocate list to maintain order
        lock = Lock()

        def download_single_image(args):
            idx, img_url = args
            try:
                response = self.session.get(img_url, timeout=30)
                response.raise_for_status()

                # Save to temporary file
                file_ext = os.path.splitext(img_url)[1] or '.jpg'
                temp_file = os.path.join(self.temp_dir, f"{idx:03d}{file_ext}")

                with open(temp_file, 'wb') as f:
                    f.write(response.content)

                with lock:
                    downloaded_files[idx - 1] = temp_file
                    print(f"  [{idx}/{len(image_urls)}] ✓ Downloaded: {os.path.basename(img_url)}")

                return True
            except Exception as e:
                with lock:
                    print(f"  [{idx}/{len(image_urls)}] ✗ Failed: {os.path.basename(img_url)} - {e}")
                return False

        # Use ThreadPoolExecutor for parallel downloads (8 threads)
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(download_single_image, (idx, url)) for idx, url in enumerate(image_urls, 1)]
            completed = sum(1 for future in as_completed(futures) if future.result())

        # Filter out None values (failed downloads)
        downloaded_files = [f for f in downloaded_files if f is not None]

        print(f"✓ Successfully downloaded {len(downloaded_files)}/{len(image_urls)} images")
        return downloaded_files

    def create_pdf(self, image_files, output_filename):
        """Create PDF from downloaded images."""
        if not image_files:
            print("✗ No images to convert to PDF")
            return

        print(f"\nCreating PDF: {output_filename}")

        try:
            # Convert all images to RGB PIL Images
            pil_images = []
            for img_file in image_files:
                try:
                    img = Image.open(img_file)
                    # Convert to RGB if necessary
                    if img.mode in ('RGBA', 'LA', 'P'):
                        rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = rgb_img
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')

                    pil_images.append(img)
                except Exception as e:
                    print(f"  ⚠ Warning: Could not process {img_file}: {e}")

            if not pil_images:
                print("✗ No valid images to create PDF")
                return

            # Save as PDF
            pil_images[0].save(
                output_filename,
                "PDF",
                resolution=100.0,
                save_all=True,
                append_images=pil_images[1:]
            )

            print(f"✓ PDF created successfully: {output_filename}")
            print(f"  Total pages: {len(pil_images)}")

        except Exception as e:
            print(f"✗ Error creating PDF: {e}")

    def cleanup(self):
        """Clean up temporary files."""
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"⚠ Warning: Could not clean up temporary files: {e}")

    def run(self, download_related=True):
        """Main execution flow."""
        try:
            # Fetch page
            html_content = self.fetch_page()

            # Detect related chapters
            related_chapters = []
            if download_related:
                related_chapters = self.detect_related_chapters(html_content)

            # Download current chapter and related chapters if found
            self.download_chapter(html_content, is_main=True)

            # Download related chapters
            if related_chapters:
                while True:
                    response = input(f"\n⭐ Found {len(related_chapters)} related chapters/parts. Download them all? (yes/no): ").strip().lower()
                    if response in ['yes', 'y']:
                        print(f"\n📦 Downloading {len(related_chapters)} related chapters...")
                        for idx, chapter in enumerate(related_chapters, 1):
                            print(f"\n[{idx}/{len(related_chapters)}] Downloading: {chapter['name']}")
                            try:
                                # Create a new downloader for each related chapter
                                related_downloader = ImageToPDFDownloader(chapter['url'], self.cookies_file)
                                related_downloader.download_chapter(related_downloader.fetch_page(), is_main=False)
                            except Exception as e:
                                print(f"  ✗ Failed to download: {e}")
                        break
                    elif response in ['no', 'n']:
                        break
                    else:
                        print("Please enter 'yes' or 'no'")

        finally:
            # Cleanup
            self.cleanup()

    def download_chapter(self, html_content, is_main=True):
        """Download images from a chapter and create PDF."""
        # Extract images
        image_urls = self.extract_images(html_content)

        if not image_urls:
            print("✗ No images found on the page")
            return

        # Download images
        downloaded_files = self.download_images(image_urls)

        if not downloaded_files:
            print("✗ No images were successfully downloaded")
            return

        # Create PDF
        output_filename = f"{self.page_title}.pdf"
        self.create_pdf(downloaded_files, output_filename)


def select_cookies_file():
    """Open file dialog to select cookies file."""
    # Create a hidden root window
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    print("\nOpening file dialog to select cookies file...")
    print("(Close the dialog or click Cancel to skip)")

    # Open file dialog
    cookies_file = filedialog.askopenfilename(
        title="Select Cookies File (or Cancel to skip)",
        filetypes=[
            ("Text files", "*.txt"),
            ("All files", "*.*")
        ],
        initialdir=os.path.expanduser("~")
    )

    root.destroy()

    if cookies_file:
        print(f"Selected: {cookies_file}")
        return cookies_file
    else:
        print("No cookies file selected")
        return None


def select_bulk_file():
    """Open file dialog to select bulk links file."""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    print("\nOpening file dialog to select bulk links file...")
    print("(Close the dialog or click Cancel to skip)")

    # Open file dialog
    bulk_file = filedialog.askopenfilename(
        title="Select Text File with Links (one per line)",
        filetypes=[
            ("Text files", "*.txt"),
            ("All files", "*.*")
        ],
        initialdir=os.path.expanduser("~")
    )

    root.destroy()

    if bulk_file:
        print(f"Selected: {bulk_file}")
        return bulk_file
    else:
        print("No file selected")
        return None


def load_urls_from_file(file_path):
    """Load URLs from a text file (one per line)."""
    urls = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                url = line.strip()
                # Skip empty lines and comments
                if url and not url.startswith('#'):
                    urls.append(url)
        print(f"✓ Loaded {len(urls)} URLs from file")
        return urls
    except Exception as e:
        print(f"✗ Error reading file: {e}")
        return []


def main():
    print("=" * 60)
    print("Web Image to PDF Downloader")
    print("=" * 60)

    # Open file dialog for cookies file once
    cookies_file = select_cookies_file()

    if cookies_file and not os.path.exists(cookies_file):
        print(f"⚠ Warning: Cookies file not found: {cookies_file}")
        cookies_file = None

    # Ask user if they want to download single or bulk
    while True:
        print("\n" + "=" * 60)
        print("Download Mode Selection")
        print("=" * 60)
        print("1. Single download (enter URLs one by one)")
        print("2. Bulk download (load URLs from text file)")
        print("3. Exit")

        mode = input("\nSelect mode (1/2/3): ").strip()

        if mode == '1':
            download_single_mode(cookies_file)
        elif mode == '2':
            download_bulk_mode(cookies_file)
        elif mode == '3':
            print("\n" + "=" * 60)
            print("Thank you! Exiting...")
            print("=" * 60)
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3")


def download_single_mode(cookies_file):
    """Handle single URL downloads."""
    print("\n" + "=" * 60)
    print("Single Download Mode")
    print("=" * 60)

    while True:
        url = input("\nEnter the webpage URL (or 'quit' to go back): ").strip()

        if url.lower() in ['quit', 'q', 'exit', 'back']:
            break

        if not url:
            print("✗ No URL provided")
            continue

        try:
            downloader = ImageToPDFDownloader(url, cookies_file)
            downloader.run()

        except Exception as e:
            print(f"✗ Error during download: {e}")
            import traceback
            traceback.print_exc()

        while True:
            another = input("\nDownload another? (yes/no): ").strip().lower()
            if another in ['yes', 'y']:
                break
            elif another in ['no', 'n']:
                return
            else:
                print("Please enter 'yes' or 'no'")


def download_bulk_mode(cookies_file):
    """Handle bulk downloads from a text file."""
    print("\n" + "=" * 60)
    print("Bulk Download Mode")
    print("=" * 60)

    bulk_file = select_bulk_file()
    if not bulk_file:
        print("✗ No file selected")
        return

    if not os.path.exists(bulk_file):
        print(f"✗ File not found: {bulk_file}")
        return

    # Load URLs from file
    urls = load_urls_from_file(bulk_file)
    if not urls:
        print("✗ No valid URLs found in file")
        return

    print(f"\n✓ Found {len(urls)} URLs to download")

    # Ask download strategy
    print("\nDownload Strategy:")
    print("1. Download one by one (ask before each)")
    print("2. Download all automatically (no confirmation)")

    strategy = input("\nSelect strategy (1/2): ").strip()

    if strategy not in ['1', '2']:
        print("Invalid choice")
        return

    auto_download = strategy == '2'

    # Process URLs
    successful = 0
    failed = 0

    for idx, url in enumerate(urls, 1):
        print(f"\n[{idx}/{len(urls)}] Processing: {url}")

        if not auto_download:
            confirm = input("Download this one? (yes/skip/quit): ").strip().lower()
            if confirm in ['quit', 'q', 'exit', 'no']:
                break
            elif confirm in ['skip', 's']:
                print("  ⊘ Skipped")
                continue

        try:
            downloader = ImageToPDFDownloader(url, cookies_file)
            downloader.run()
            successful += 1

        except Exception as e:
            print(f"  ✗ Error: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print("Bulk Download Complete!")
    print("=" * 60)
    print(f"Successful: {successful}/{len(urls)}")
    print(f"Failed: {failed}/{len(urls)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
