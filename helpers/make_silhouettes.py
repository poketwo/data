import os
from PIL import Image

# === CONFIG ===
source_dir = "images"
target_dir = "silhouettes"

# Ensure directories exist
if not os.path.exists(source_dir):
    print(f"Directory {source_dir} doesn't exist")
    quit()

if not os.path.exists(target_dir):
    print(f"Directory {target_dir} doesn't exist")
    quit()

# Supported image formats
valid_extensions = {".png"}

for filename in os.listdir(source_dir):
    name, ext = os.path.splitext(filename)
    if ext.lower() not in valid_extensions:
        continue  # skip non-image files
    
    src_path = os.path.join(source_dir, filename)
    dst_path = os.path.join(target_dir, filename)
    
    # Skip if file already exists
    if os.path.exists(dst_path):
        continue

    # Open image
    img = Image.open(src_path).convert("RGBA")
    pixels = img.load()

    # Iterate over all pixels and modify non-transparent ones
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = pixels[x, y]
            if a > 0:  # non-transparent
                pixels[x, y] = (0, 0, 0, a)  # make black but keep alpha

    img.save(dst_path)
    print(f"Saved processed image: {dst_path}")

print("✅ Conversion complete.")

