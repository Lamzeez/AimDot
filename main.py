import os
import sys
import json
import threading
import winreg
import ctypes
import tkinter as tk
from PIL import Image, ImageDraw
import pystray

# Set process DPI awareness to ensure pixel-perfect screen centering
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# --- CONSTANTS & WINDOWS API SETUP ---
MUTEX_NAME = "Global\\AimDotMutex_987654"
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
LWA_COLORKEY = 0x00000001

# Window size (small, lightweight box exactly centered on the screen)
WINDOW_WIDTH = 100
WINDOW_HEIGHT = 100
CANVAS_CENTER_X = WINDOW_WIDTH // 2
CANVAS_CENTER_Y = WINDOW_HEIGHT // 2

# Default Configuration (made smaller by default)
DEFAULT_CONFIG = {
    "color": "red",
    "size": 4,       # Default size is now 4 (Medium)
    "shape": "dot",  # "dot", "crosshair", "circle", "dot_circle"
    "visible": True,
    "startup": False
}

# Supported sizes mapping (shifted down for smaller options)
SIZES = {
    "Tiny (2px)": 2,
    "Small (3px)": 3,
    "Medium (4px)": 4,
    "Large (6px)": 6,
    "Extra Large (10px)": 10
}

# Reverse sizes mapping for menu display
REVERSE_SIZES = {v: k for k, v in SIZES.items()}

# Supported shapes
SHAPES = {
    "Solid Dot": "dot",
    "Crosshair": "crosshair",
    "Circle": "circle",
    "Dot + Circle": "dot_circle"
}
REVERSE_SHAPES = {v: k for k, v in SHAPES.items()}

# Supported colors
COLORS = {
    "Red": "red",
    "Green": "#00FF00",
    "Blue": "#0077FF",
    "Yellow": "yellow",
    "Cyan": "cyan",
    "Magenta": "magenta",
    "White": "white"
}
REVERSE_COLORS = {v: k for k, v in COLORS.items()}


# --- CONFIGURATION PERSISTENCE ---
def get_config_path():
    """Get the path to the configuration file in Local AppData."""
    appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    dir_path = os.path.join(appdata, "AimDot")
    os.makedirs(dir_path, exist_ok=True)
    return os.path.join(dir_path, "config.json")

def load_config():
    """Load configuration, falling back to defaults if missing or corrupted."""
    path = get_config_path()
    config = DEFAULT_CONFIG.copy()
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                loaded = json.load(f)
                # Verify keys and merge
                for k, v in loaded.items():
                    if k in config:
                        config[k] = v
        except Exception:
            pass
    return config

def save_config(config):
    """Save current configuration to AppData."""
    path = get_config_path()
    try:
        with open(path, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")


# --- WINDOWS STARTUP REGISTRY MANAGEMENT ---
def set_startup_registry(enabled):
    """Register/unregister the app in HKEY_CURRENT_USER Run key."""
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "AimDot"
    
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        exe_path = f'"{sys.executable}"'
    else:
        # Running as raw script
        exe_path = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
        
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enabled:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass
            except Exception as e:
                print(f"Error deleting registry value: {e}")
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Error modifying startup registry: {e}")
        return False


# --- SINGLE INSTANCE ENFORCEMENT ---
# Keep reference to the mutex so it is not garbage collected
_mutex_holder = None

def check_single_instance():
    """Ensure only one instance runs in the background using a global named Mutex."""
    global _mutex_holder
    _mutex_holder = ctypes.windll.kernel32.CreateMutexW(None, True, MUTEX_NAME)
    last_error = ctypes.windll.kernel32.GetLastError()
    if last_error == 183: # ERROR_ALREADY_EXISTS
        # Show a user-friendly message
        ctypes.windll.user32.MessageBoxW(
            0, 
            "Aim Dot is already running in the background!\n\nYou can access and customize it from your Windows system tray (near the clock).", 
            "Aim Dot", 
            0x40 | 0x0 # MB_OK | MB_ICONINFORMATION
        )
        sys.exit(0)


# --- DYNAMIC SYSTEM TRAY ICON GENERATION ---
def create_tray_icon_image():
    """Create a high-contrast reticle icon for the system tray."""
    img = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0)) # Transparent
    draw = ImageDraw.Draw(img)
    
    # Draw a stylish target reticle
    draw.ellipse((8, 8, 56, 56), outline="white", width=4)
    draw.ellipse((24, 24, 40, 40), fill="red")
    
    # Draw crosshair notches
    draw.rectangle((30, 4, 34, 16), fill="white")
    draw.rectangle((30, 48, 34, 60), fill="white")
    draw.rectangle((4, 30, 16, 34), fill="white")
    draw.rectangle((48, 30, 60, 34), fill="white")
    return img


# --- MAIN APPLICATION CLASS ---
class AimDotApp:
    def __init__(self):
        # 1. Enforce single instance
        check_single_instance()
        
        # 2. Load settings
        self.config = load_config()
        
        # 3. Create GUI
        self.root = tk.Tk()
        self.root.title("Aim Dot")
        
        # Configure window traits
        self.root.overrideredirect(True)       # Borderless
        self.root.attributes("-topmost", True) # Always on top
        self.root.configure(bg='black')       # Black bg for transparency key
        
        # Prevent appearing in taskbar (on Windows, toolwindow style does this nicely)
        self.root.attributes("-toolwindow", True)
        
        # Create canvas for drawing the overlay shapes
        # Explicitly set borderwidth=0 and highlightthickness=0 to completely eliminate
        # any grey 3D reliefs or default system window border shading.
        self.canvas = tk.Canvas(
            self.root, 
            width=WINDOW_WIDTH, 
            height=WINDOW_HEIGHT, 
            bg='black', 
            highlightthickness=0,
            borderwidth=0
        )
        self.canvas.pack(fill="both", expand=True)
        
        # Position and style setup
        self.reposition_window()
        self.draw_shapes()
        
        # Inject click-through and native transparency styles once the window is initialized
        self.root.after(50, self.apply_click_through)
        
        # Start the periodic position & topmost enforcement loop
        self.root.after(2000, self.periodic_enforce)
        
        # 4. Set up Tray Icon
        self.tray_icon = None
        self.setup_tray()

    def get_true_hwnd(self):
        """Get the true top-level Win32 HWND of the Tkinter window using a dual-strategy approach."""
        # Strategy A: Use wm_frame
        try:
            frame_str = self.root.wm_frame()
            if frame_str:
                return int(frame_str, 16)
        except Exception:
            pass
            
        # Strategy B: Recursive GetParent traversal from winfo_id
        try:
            hwnd = self.root.winfo_id()
            while True:
                parent = ctypes.windll.user32.GetParent(hwnd)
                if not parent:
                    break
                hwnd = parent
            return hwnd
        except Exception:
            pass
            
        return None

    def reposition_window(self):
        """Align the overlay window's center with the physical center of the primary monitor."""
        # Get actual screen dimensions (unscaled)
        screen_width = ctypes.windll.user32.GetSystemMetrics(0)
        screen_height = ctypes.windll.user32.GetSystemMetrics(1)
        
        # Calculate upper-left coordinates
        x = (screen_width - WINDOW_WIDTH) // 2
        y = (screen_height - WINDOW_HEIGHT) // 2
        
        # Apply geometry
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")

    def apply_click_through(self):
        """Inject Windows EX_STYLE to make the entire window click-through AND natively transparent."""
        try:
            # Force Tkinter to fully create and map the Windows window frame
            self.root.update()
            
            hwnd = self.get_true_hwnd()
            if not hwnd:
                print("Error: Could not retrieve valid Win32 HWND.")
                return
            
            # 1. Fetch current window style
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            
            # 2. Set click-through and layered style bits
            ctypes.windll.user32.SetWindowLongW(
                hwnd, 
                GWL_EXSTYLE, 
                style | WS_EX_TRANSPARENT | WS_EX_LAYERED
            )
            
            # 3. Apply the transparency colorkey (0x00000000 is pure black)
            # This makes all black pixels (bg='black') fully transparent on the desktop
            ctypes.windll.user32.SetLayeredWindowAttributes(
                hwnd, 
                0,             # crKey = 0 (black in COLORREF format)
                0,             # bAlpha = 0 (ignored for LWA_COLORKEY)
                LWA_COLORKEY   # dwFlags = 1 (LWA_COLORKEY)
            )
        except Exception as e:
            print(f"Error applying click-through style: {e}")

    def draw_shapes(self):
        """Clear canvas and draw the selected reticle shape based on current configuration."""
        self.canvas.delete("all")
        
        if not self.config["visible"]:
            return
            
        color = self.config["color"]
        size = self.config["size"]
        shape = self.config["shape"]
        
        cx, cy = CANVAS_CENTER_X, CANVAS_CENTER_Y
        
        if shape == "dot":
            # Drawing a mathematically perfect, anti-aliased-looking symmetric circle
            # on the discrete pixel grid by plotting exact symmetric pixel rows.
            # This completely bypasses standard Tkinter create_oval rounding bugs.
            if size == 2:
                # Perfect 2x2 Square Dot
                self.canvas.create_rectangle(cx - 1, cy - 1, cx + 1, cy + 1, fill=color, outline="")
            elif size == 3:
                # Perfect Symmetric 3px Rounded Cross
                # Row 1 (y=cy-1): width 1 centered
                self.canvas.create_rectangle(cx, cy - 1, cx + 1, cy, fill=color, outline="")
                # Row 2 (y=cy): width 3 centered
                self.canvas.create_rectangle(cx - 1, cy, cx + 2, cy + 1, fill=color, outline="")
                # Row 3 (y=cy+1): width 1 centered
                self.canvas.create_rectangle(cx, cy + 1, cx + 1, cy + 2, fill=color, outline="")
            elif size == 4:
                # Perfect Symmetric 4px Rounded Circle
                # Row 1: width 2 (x: cx-1 to cx+1)
                self.canvas.create_rectangle(cx - 1, cy - 2, cx + 1, cy - 1, fill=color, outline="")
                # Rows 2-3: width 4 (x: cx-2 to cx+2)
                self.canvas.create_rectangle(cx - 2, cy - 1, cx + 2, cy + 1, fill=color, outline="")
                # Row 4: width 2 (x: cx-1 to cx+1)
                self.canvas.create_rectangle(cx - 1, cy + 1, cx + 1, cy + 2, fill=color, outline="")
            elif size == 6:
                # Perfect Symmetric 6px Rounded Circle
                # Row 1: width 4
                self.canvas.create_rectangle(cx - 2, cy - 3, cx + 2, cy - 2, fill=color, outline="")
                # Rows 2-5: width 6
                self.canvas.create_rectangle(cx - 3, cy - 2, cx + 3, cy + 2, fill=color, outline="")
                # Row 6: width 4
                self.canvas.create_rectangle(cx - 2, cy + 2, cx + 2, cy + 3, fill=color, outline="")
            else: # size == 10
                # Perfect Symmetric 10px Rounded Circle
                # Row 1: width 4
                self.canvas.create_rectangle(cx - 2, cy - 5, cx + 2, cy - 4, fill=color, outline="")
                # Row 2: width 6
                self.canvas.create_rectangle(cx - 3, cy - 4, cx + 3, cy - 3, fill=color, outline="")
                # Row 3: width 8
                self.canvas.create_rectangle(cx - 4, cy - 3, cx + 4, cy - 2, fill=color, outline="")
                # Rows 4-7: width 10
                self.canvas.create_rectangle(cx - 5, cy - 2, cx + 5, cy + 2, fill=color, outline="")
                # Row 8: width 8
                self.canvas.create_rectangle(cx - 4, cy + 2, cx + 4, cy + 3, fill=color, outline="")
                # Row 9: width 6
                self.canvas.create_rectangle(cx - 3, cy + 3, cx + 3, cy + 4, fill=color, outline="")
                # Row 10: width 4
                self.canvas.create_rectangle(cx - 2, cy + 4, cx + 2, cy + 5, fill=color, outline="")
            
        elif shape == "crosshair":
            # Tactical crosshair with small center gap
            thickness = max(1, size // 3)
            gap = 3.0
            length = 10.0
            # Left arm
            self.canvas.create_line(cx - length, cy, cx - gap, cy, fill=color, width=thickness)
            # Right arm
            self.canvas.create_line(cx + gap, cy, cx + length, cy, fill=color, width=thickness)
            # Top arm
            self.canvas.create_line(cx, cy - length, cx, cy - gap, fill=color, width=thickness)
            # Bottom arm
            self.canvas.create_line(cx, cy + gap, cx, cy + length, fill=color, width=thickness)
            
        elif shape == "circle":
            # Hollow tactical ring
            thickness = max(1, size // 3)
            radius = 6.0
            self.canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, outline=color, width=thickness, fill="")
            
        elif shape == "dot_circle":
            # Centered dot + surrounding ring
            dot_r = max(1, size / 4.0)
            self.canvas.create_oval(cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r, fill=color, outline="")
            
            thickness = max(1, size // 4)
            outer_r = 8.0
            self.canvas.create_oval(cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r, outline=color, width=thickness, fill="")

    def periodic_enforce(self):
        """Periodically ensure the overlay is centered, on-top, and visible."""
        if self.root:
            try:
                self.reposition_window()
                self.root.attributes("-topmost", True)
                self.root.lift()
                # Schedule next run
                self.root.after(2000, self.periodic_enforce)
            except Exception:
                pass

    def update_overlay(self):
        """Trigger redraw in the main GUI thread."""
        self.root.after(0, self.draw_shapes)

    # --- TRAY CONTROL HANDLERS ---
    def set_shape(self, shape_name):
        self.config["shape"] = SHAPES[shape_name]
        save_config(self.config)
        self.update_overlay()
        self.update_tray_menu()

    def set_size(self, size_name):
        self.config["size"] = SIZES[size_name]
        save_config(self.config)
        self.update_overlay()
        self.update_tray_menu()

    def set_color(self, color_name):
        self.config["color"] = COLORS[color_name]
        save_config(self.config)
        self.update_overlay()
        self.update_tray_menu()

    def toggle_visibility(self):
        self.config["visible"] = not self.config["visible"]
        save_config(self.config)
        self.update_overlay()
        self.update_tray_menu()

    def toggle_startup(self):
        new_val = not self.config["startup"]
        if set_startup_registry(new_val):
            self.config["startup"] = new_val
            save_config(self.config)
        self.update_tray_menu()

    def show_about(self):
        """Show information window using system API thread-safely."""
        self.root.after(0, lambda: ctypes.windll.user32.MessageBoxW(
            0,
            "Aim Dot v1.3.0\n\nA professional, ultra-lightweight, and fully customizable screen overlay utility.\n\nCreated by Antigravity AI.",
            "About Aim Dot",
            0x40 | 0x0
        ))

    def quit_app(self):
        """Clean shut down of both Tkinter and pystray icon threads."""
        # Stop tray icon
        if self.tray_icon:
            self.tray_icon.stop()
        # Destroy GUI
        self.root.after(0, self.root.destroy)

    # --- CLOSURE FACTORIES FOR PYSTRAY COMPLIANCE ---
    def make_shape_action(self, label):
        return lambda icon, item: self.set_shape(label)

    def make_shape_checked(self, label):
        return lambda item: self.config["shape"] == SHAPES[label]

    def make_color_action(self, label):
        return lambda icon, item: self.set_color(label)

    def make_color_checked(self, label):
        return lambda item: self.config["color"] == COLORS[label]

    def make_size_action(self, label):
        return lambda icon, item: self.set_size(label)

    def make_size_checked(self, label):
        return lambda item: self.config["size"] == SIZES[label]

    # --- SYSTEM TRAY MENU BUILDER ---
    def build_tray_menu(self):
        """Construct the menu structure based on current dynamic config."""
        
        # 1. Shapes Submenu
        shape_items = []
        for s_label in SHAPES.keys():
            shape_items.append(pystray.MenuItem(
                s_label,
                self.make_shape_action(s_label),
                checked=self.make_shape_checked(s_label),
                radio=True
            ))
            
        # 2. Colors Submenu
        color_items = []
        for c_label in COLORS.keys():
            color_items.append(pystray.MenuItem(
                c_label,
                self.make_color_action(c_label),
                checked=self.make_color_checked(c_label),
                radio=True
            ))
            
        # 3. Sizes Submenu
        size_items = []
        for sz_label in SIZES.keys():
            size_items.append(pystray.MenuItem(
                sz_label,
                self.make_size_action(sz_label),
                checked=self.make_size_checked(sz_label),
                radio=True
            ))

        # Main Menu
        return pystray.Menu(
            pystray.MenuItem('Show Overlay', lambda icon, item: self.toggle_visibility(), checked=lambda item: self.config["visible"]),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Shape', pystray.Menu(*shape_items)),
            pystray.MenuItem('Color', pystray.Menu(*color_items)),
            pystray.MenuItem('Size', pystray.Menu(*size_items)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Run at Startup', lambda icon, item: self.toggle_startup(), checked=lambda item: self.config["startup"]),
            pystray.MenuItem('About Aim Dot', lambda icon, item: self.show_about()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Exit', lambda icon, item: self.quit_app())
        )

    def setup_tray(self):
        """Initialize the tray icon running on its own background thread."""
        img = create_tray_icon_image()
        self.tray_icon = pystray.Icon(
            "AimDot", 
            img, 
            "Aim Dot", 
            self.build_tray_menu()
        )
        
        # Start pystray mainloop in a separate thread
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()

    def update_tray_menu(self):
        """Update system tray menu items to reflect new state changes."""
        if self.tray_icon:
            self.tray_icon.menu = self.build_tray_menu()

    def run(self):
        """Start the main GUI loop."""
        self.root.mainloop()


if __name__ == "__main__":
    app = AimDotApp()
    app.run()
