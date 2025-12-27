import os
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Configuration
# Variable font URL - Outfit font weight 700 to match UI
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/outfit/Outfit%5Bwght%5D.ttf"
FONT_PATH = "Outfit.ttf"
SYSTEM_FONT_PATH = "/Library/Fonts/Arial Unicode.ttf"
PRIMARY_COLOR = "#6c63ff"
GLOW_COLOR = (108, 99, 255, 100)  # Primary color with alpha for glow
OUTPUT_DIR = "../static/img"

# Icon dimensions - 512x512 for high resolution
ICON_SIZE = 512

def download_font():
    # Try downloading Outfit
    if not os.path.exists(FONT_PATH):
        print(f"Downloading font from {FONT_URL}...")
        try:
            response = requests.get(FONT_URL)
            if response.status_code == 200:
                with open(FONT_PATH, 'wb') as f:
                    f.write(response.content)
                print("Font downloaded.")
                return FONT_PATH
            else:
                print(f"Failed to download font. Status: {response.status_code}")
        except Exception as e:
            print(f"Download error: {e}")
    else:
        return FONT_PATH
    
    # Fallback to system font
    if os.path.exists(SYSTEM_FONT_PATH):
        print(f"Using system font: {SYSTEM_FONT_PATH}")
        return SYSTEM_FONT_PATH
    
    return None

def create_icon(size, filename, bg_color=None, font_path=None, add_glow=False):
    # Create image
    if bg_color:
        img = Image.new('RGBA', (size, size), bg_color)
    else:
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0)) # Transparent

    draw = ImageDraw.Draw(img)

    # Load font
    font = None
    try:
        if font_path:
            # Font size proportional to icon size
            # Much heavier weight with less padding to match UI reference
            font_size = int(size * 0.95) 
            font = ImageFont.truetype(font_path, font_size)
            # Set font weight to 800 (Extra Bold) for variable font
            try:
                font.set_variation_by_axes([800])  # Weight axis
            except Exception:
                pass  # Not a variable font or variation not supported
    except Exception as e:
        print(f"Error loading font {font_path}: {e}")

    if font is None:
        print("Using default font (warning: small size).")
        font = ImageFont.load_default()

    # Calculate text position to center it
    text = "V"
    
    # Get bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Center position
    x = (size - text_width) / 2 - bbox[0]
    y = (size - text_height) / 2 - bbox[1]

    # Add glow effect for apple-touch-icon
    if add_glow:
        # Create glow layer
        glow_layer = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)
        
        # Draw text in glow color (multiple times for stronger effect)
        for offset in range(3):
            glow_draw.text((x, y), text, font=font, fill=GLOW_COLOR)
        
        # Apply gaussian blur for glow effect
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=size * 0.05))
        
        # Composite glow under the main image
        img = Image.alpha_composite(img, glow_layer)
        draw = ImageDraw.Draw(img)

    # Draw text
    draw.text((x, y), text, font=font, fill=PRIMARY_COLOR)

    # Save
    output_path = os.path.join(OUTPUT_DIR, filename)
    img.save(output_path)
    print(f"Saved {output_path} ({size}x{size})")

def main():
    # Ensure output dir exists
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Get font
    font_path = download_font()

    # Favicon (180x180, transparent background)
    create_icon(ICON_SIZE, "favicon.png", bg_color=None, font_path=font_path)

    # Apple Touch Icon (512x512, white background, with glow effect)
    create_icon(ICON_SIZE, "apple-touch-icon.png", bg_color="white", font_path=font_path, add_glow=True)

    # Cleanup downloaded font file if it exists and we downloaded it (not system)
    if font_path == FONT_PATH and os.path.exists(FONT_PATH):
        try:
            os.remove(FONT_PATH)
        except:
            pass

if __name__ == "__main__":
    main()
