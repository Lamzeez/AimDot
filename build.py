import os
import sys
import shutil
import subprocess
from PIL import Image, ImageDraw

def generate_ico():
    """Generates a beautiful high-resolution multi-size .ico file for the executable."""
    print("Generating custom application icon...")
    # Sizes standard for Windows icons
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    images = []
    
    for size in sizes:
        w, h = size
        img = Image.new('RGBA', (w, h), color=(0, 0, 0, 0)) # transparent
        draw = ImageDraw.Draw(img)
        
        # Scale design elements relative to the image size
        padding = max(2, w // 8)
        border_w = max(1, w // 16)
        center_r = max(1, w // 6)
        
        # Draw outer ring
        draw.ellipse((padding, padding, w - padding, h - padding), outline="white", width=border_w)
        # Draw center red dot
        cx, cy = w // 2, h // 2
        draw.ellipse((cx - center_r, cy - center_r, cx + center_r, cy + center_r), fill="red")
        
        # Draw crosshair notch lines
        notch_w = max(1, w // 16)
        # Top
        draw.rectangle((cx - notch_w // 2, padding // 2, cx + notch_w // 2, padding + border_w), fill="white")
        # Bottom
        draw.rectangle((cx - notch_w // 2, h - padding - border_w, cx + notch_w // 2, h - padding // 2), fill="white")
        # Left
        draw.rectangle((padding // 2, cy - notch_w // 2, padding + border_w, cy + notch_w // 2), fill="white")
        # Right
        draw.rectangle((w - padding - border_w, cy - notch_w // 2, w - padding // 2, cy + notch_w // 2), fill="white")
        
        images.append(img)
        
    # Save as .ico file supporting multiple resolutions
    ico_path = "icon.ico"
    images[-1].save(ico_path, format='ICO', sizes=sizes, append_images=images[:-1])
    print(f"Icon created successfully: {os.path.abspath(ico_path)}")
    return ico_path

def build_executable():
    """Compiles main.py to a standalone Aim Dot.exe using PyInstaller."""
    ico_path = generate_ico()
    
    cmd = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        f"--icon={ico_path}",
        "--clean",
        "--name", "Aim Dot",
        "main.py"
    ]
    
    print("\nRunning PyInstaller to compile standalone executable...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        # Run pyinstaller
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Compilation complete!")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("\n[ERROR] PyInstaller failed during compilation!")
        print(e.stdout)
        print(e.stderr)
        sys.exit(1)
        
    # Move executable to root directory and cleanup build files
    dest_path = "Aim Dot.exe"
    dist_path = os.path.join("dist", "Aim Dot.exe")
    
    if os.path.exists(dist_path):
        # Remove old exe in root if it exists
        if os.path.exists(dest_path):
            os.remove(dest_path)
            
        shutil.move(dist_path, dest_path)
        print(f"\n[SUCCESS] Standalone executable built: {os.path.abspath(dest_path)}")
    else:
        print("\n[ERROR] Could not find compiled executable in dist directory.")
        sys.exit(1)
        
    # Clean up PyInstaller build artifacts
    print("\nCleaning up temporary build artifacts...")
    folders_to_delete = ["build", "dist"]
    files_to_delete = ["Aim Dot.spec", "icon.ico"]
    
    for folder in folders_to_delete:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            
    for file in files_to_delete:
        if os.path.exists(file):
            os.remove(file)
            
    print("Cleanup completed! Workspace is clean and pristine.")

if __name__ == "__main__":
    build_executable()
