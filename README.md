# Aim Dot

**Aim Dot** is a professional, ultra-lightweight, and fully customizable screen overlay utility for Windows. It displays an always-on-top, click-through crosshair or dot exactly in the center of your screen. It runs silently in the background and can be easily customized from your Windows system tray.

---

## Key Features

- 🎯 **Natively Transparent:** Uses hardware-accelerated Windows API colorkeying on the top-level window handle (`HWND`) to make the background 100% transparent. No black boxes or gray borders.
- 🖱️ **Fully Click-Through:** Standard mouse clicks and movements pass directly through the overlay, ensuring it never interferes with games or application windows.
- 💻 **DPI-Aware & Centered:** Dynamically queries Windows for real unscaled primary monitor dimensions, positioning the dot at the *exact* physical center of your screen.
- ⚙️ **System Tray Controls:** Right-click the system tray icon (near your clock) to customize settings on the fly:
  - **Show/Hide:** Easily toggle overlay visibility.
  - **Shapes:** Choose between *Solid Dot*, *Crosshair*, *Circle*, and *Dot + Circle*.
  - **Colors:** Support for *Red*, *Green*, *Blue*, *Yellow*, *Cyan*, *Magenta*, and *White*.
  - **Sizes:** Five granular size configurations from *Tiny (2px)* up to *Extra Large (10px)*.
  - **Run at Startup:** Toggle option to automatically launch Aim Dot when Windows boots up.
  - **Exit:** Gracefully shut down the background process.
- 🔒 **Single Instance Enforced:** Utilizes a global named Windows Mutex to ensure only one instance runs at any time.

---

## Sizing Presets

We hand-coded the exact pixel spans row-by-row for each selectable size to ensure perfect mathematical symmetry on the pixel grid (bypassing GDI vector rounding issues):

- **Tiny:** 2px
- **Small:** 3px
- **Medium:** 4px *(Default)*
- **Large:** 6px
- **Extra Large:** 10px

---

## How to Use

1. **Download:** Clone this repository or download [Aim Dot.exe](./Aim%20Dot.exe).
2. **Run:** Double-click the compiled **`Aim Dot.exe`**.
3. **Customize:** Right-click the reticle icon in your **Windows system tray** (near the clock) to adjust settings.
4. **Close:** Right-click the system tray icon and click **Exit**, or close it in Windows Task Manager.

---

## Build from Source (Optional)

If you wish to compile the executable yourself, make sure you have Python 3 installed, then:

1. Install the required packaging dependencies:
   ```bash
   pip install pystray pillow pyinstaller
   ```
2. Run the automated build script:
   ```bash
   python build.py
   ```
The script will dynamically generate a high-resolution multi-size application icon (`icon.ico`), package the application into a console-free single-file executable `Aim Dot.exe` at the project root, and cleanly delete temporary build artifacts.
