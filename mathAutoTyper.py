import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
from pynput import keyboard
from pynput.keyboard import Key, Controller as KeyboardController
import sys
import ctypes
from ctypes import wintypes

class MathAutoTyper:
    def __init__(self, root):
        self.root = root
        self.root.title("Math Auto Typer")
        self.root.geometry("600x400")
        
        # Darker color scheme
        self.bg_color = "#0f0f0f"  # Darker main background
        self.surface_color = "#151515"  # Darker panel background
        self.accent_color = "#1a1a1a"  # Darker hover/selected
        self.text_color = "#b0b0b0"  # Slightly dimmer primary text
        self.text_secondary = "#666666"  # Darker secondary text
        self.border_color = "#2a2a2a"  # Darker borders
        self.button_bg = "#2a2a2a"  # Darker button background
        self.button_hover = "#333333"  # Darker button hover
        self.close_hover = "#cc0f1f"  # Slightly darker close button hover
        self.title_bar_bg = "#1a1a1a"  # Darker title bar
        self.soft_border = "#333333"  # Darker soft gray border
        
        # Configure root background
        self.root.configure(bg=self.soft_border)
        
        # Make window stay on top
        self.root.attributes('-topmost', True)
        
        # Make window frameless
        self.root.overrideredirect(True)
        
        # Add soft gray border frame with rounded corners
        self.border_frame = tk.Frame(self.root, bg=self.soft_border, bd=0)
        self.border_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Create rounded container
        self.content_frame = tk.Frame(self.border_frame, bg=self.bg_color, bd=0)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Window state
        self.is_maximized = False
        self.normal_geometry = None
        
        # Drag state
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # Keyboard controller for typing
        self.keyboard_controller = KeyboardController()
        
        # Hotkey listener
        self.hotkey_listener = None
        self.hotkey_key = keyboard.KeyCode.from_char('`')
        self.hotkey_pressed = False
        
        # Typing state
        self.is_typing = False
        self.text_to_type = ""
        
        self.setup_ui()
        self.setup_hotkey()
    
    def register_taskbar_window(self):
        """Register window to show in taskbar on Windows"""
        try:
            if sys.platform == "win32":
                # Get window handle - tkinter's winfo_id() returns the HWND directly
                hwnd = self.root.winfo_id()
                
                # Verify we have a valid handle
                if not hwnd:
                    return
                
                # Set window attributes for taskbar
                # For frameless windows, we need to explicitly set WS_EX_APPWINDOW
                GWL_EXSTYLE = -20
                WS_EX_APPWINDOW = 0x00040000
                WS_EX_TOOLWINDOW = 0x00000080
                WS_EX_NOACTIVATE = 0x08000000
                
                # Get current extended style
                exstyle = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                
                # Remove toolwindow and noactivate flags, add appwindow flag
                # This ensures the window appears in the taskbar
                exstyle = exstyle & ~WS_EX_TOOLWINDOW
                exstyle = exstyle & ~WS_EX_NOACTIVATE
                exstyle = exstyle | WS_EX_APPWINDOW
                
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle)
                
                # Force window update
                SW_SHOW = 5
                ctypes.windll.user32.ShowWindow(hwnd, SW_SHOW)
                
                # Update window
                ctypes.windll.user32.UpdateWindow(hwnd)
                
                # Use SetWindowPos to ensure proper registration
                HWND_TOP = 0
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                SWP_NOZORDER = 0x0004
                SWP_FRAMECHANGED = 0x0020
                
                ctypes.windll.user32.SetWindowPos(
                    hwnd, HWND_TOP, 0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED
                )
        except Exception as e:
            print(f"Taskbar registration error: {e}")  # Debug output
        
    def apply_rounded_corners(self):
        """Apply rounded corners to the window (Windows 11 style)"""
        try:
            if sys.platform == "win32":
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
                if not hwnd:
                    hwnd = self.root.winfo_id()
                
                # Windows 11 rounded corners
                DWMWA_WINDOW_CORNER_PREFERENCE = 33
                DWMWCP_ROUND = 2
                
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_WINDOW_CORNER_PREFERENCE,
                    ctypes.byref(ctypes.c_int(DWMWCP_ROUND)),
                    ctypes.sizeof(ctypes.c_int)
                )
        except Exception:
            pass  # Fallback if Windows API calls fail
        
    def setup_ui(self):
        # Custom title bar matching Cursor's style
        title_bar = tk.Frame(self.content_frame, bg=self.title_bar_bg, height=32)
        title_bar.pack(fill=tk.X)
        title_bar.pack_propagate(False)
        
        # Make title bar draggable
        title_bar.bind("<Button-1>", self.start_drag)
        title_bar.bind("<B1-Motion>", self.on_drag)
        
        # Title text - Cursor style
        title_text = tk.Label(
            title_bar,
            text="Math Auto Typer",
            font=("Segoe UI", 12, "normal"),
            fg=self.text_color,
            bg=self.title_bar_bg
        )
        title_text.pack(side=tk.LEFT, padx=12)
        title_text.bind("<Button-1>", self.start_drag)
        title_text.bind("<B1-Motion>", self.on_drag)
        
        # Window control buttons frame
        button_frame = tk.Frame(title_bar, bg=self.title_bar_bg)
        button_frame.pack(side=tk.RIGHT, padx=0)
        
        # Minimize button - Cursor style
        self.minimize_btn_frame, _ = self.create_round_button(
            button_frame, "−", self.minimize_window, self.button_bg, hover_color=self.button_hover
        )
        self.minimize_btn_frame.pack(side=tk.LEFT, padx=0)
        
        # Maximize/Restore button - Cursor style
        self.maximize_btn_frame, self.maximize_btn_canvas = self.create_round_button(
            button_frame, "□", self.toggle_maximize, self.button_bg, hover_color=self.button_hover
        )
        self.maximize_btn_frame.pack(side=tk.LEFT, padx=0)
        
        # Screenshot button - SS label (slightly wider for two characters)
        self.screenshot_btn_frame, _ = self.create_round_button(
            button_frame, "SS", self.take_screenshot, self.button_bg, hover_color=self.button_hover, width=52
        )
        self.screenshot_btn_frame.pack(side=tk.LEFT, padx=0)
        
        # Close button - Cursor style
        self.close_btn_frame, _ = self.create_round_button(
            button_frame, "×", self.close_window, self.button_bg, hover_color=self.close_hover
        )
        self.close_btn_frame.pack(side=tk.LEFT, padx=0)
        
        # Discreet credits below title bar
        credits_bar = tk.Frame(self.content_frame, bg=self.bg_color, height=32)
        credits_bar.pack(fill=tk.X)
        credits_bar.pack_propagate(False)
        
        # Credits container on the right
        credits_container = tk.Frame(credits_bar, bg=self.bg_color)
        credits_container.pack(side=tk.RIGHT, padx=8, pady=2)
        
        credits_label = tk.Label(
            credits_container,
            text="made by Ajmal",
            font=("Segoe UI", 7),
            fg="#d0d0d0",  # Light grayish white - more eye-catching
            bg=self.bg_color
        )
        credits_label.pack()
        
        # Instagram handle with bold "IG"
        instagram_frame = tk.Frame(credits_container, bg=self.bg_color)
        instagram_frame.pack()
        
        # Bold "IG" label
        ig_label = tk.Label(
            instagram_frame,
            text="IG",
            font=("Segoe UI", 7, "bold"),
            fg="#d0d0d0",  # Light grayish white
            bg=self.bg_color
        )
        ig_label.pack(side=tk.LEFT, padx=(0, 4))
        
        instagram_label = tk.Label(
            instagram_frame,
            text="@ajmal_hanifa",
            font=("Segoe UI", 7),
            fg="#d0d0d0",  # Same light grayish white
            bg=self.bg_color
        )
        instagram_label.pack(side=tk.LEFT)
        
        # Main container with padding
        main_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Instructions - Cursor style
        instructions = tk.Label(
            main_frame,
            text="Enter text below. Press ` (backtick) to type it character by character.",
            font=("Segoe UI", 10),
            fg=self.text_secondary,
            bg=self.bg_color
        )
        instructions.pack(pady=(0, 12))
        
        # Text input area
        text_frame = tk.Frame(main_frame, bg=self.bg_color)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        # Label for text area - Cursor style
        text_label = tk.Label(
            text_frame,
            text="Text to Type:",
            font=("Segoe UI", 11),
            fg=self.text_color,
            bg=self.bg_color,
            anchor="w"
        )
        text_label.pack(fill=tk.X, pady=(0, 8))
        
        # Create text widget and custom scrollbar separately for better control
        self.text_input = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=("Consolas", 12),  # Cursor uses Consolas/JetBrains Mono
            bg=self.surface_color,
            fg=self.text_color,
            insertbackground="#888888",  # Darker cursor color
            selectbackground="#1a3d5a",  # Darker selection color
            selectforeground=self.text_color,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=self.border_color,
            highlightcolor=self.border_color,
            padx=14,
            pady=14
        )
        
        # Create ttk scrollbar with custom style for better color control
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure scrollbar style
        style.configure("Custom.Vertical.TScrollbar",
                       background=self.border_color,
                       troughcolor=self.surface_color,
                       darkcolor=self.surface_color,
                       lightcolor=self.surface_color,
                       bordercolor=self.surface_color,
                       arrowcolor=self.text_secondary,
                       activebackground=self.text_secondary)
        
        # Create custom scrollbar with gray theme
        scrollbar = ttk.Scrollbar(
            text_frame,
            orient=tk.VERTICAL,
            command=self.text_input.yview,
            style="Custom.Vertical.TScrollbar"
        )
        
        # Link text widget and scrollbar
        self.text_input.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.text_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure text widget tags for Cursor styling
        self.text_input.config(insertwidth=2)
        
        # Status bar - Cursor style
        status_frame = tk.Frame(main_frame, bg=self.surface_color, height=22)
        status_frame.pack(fill=tk.X, pady=(12, 0))
        status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(
            status_frame,
            text="Ready | Hotkey: `",
            font=("Segoe UI", 10),
            fg=self.text_secondary,
            bg=self.surface_color,
            anchor="w"
        )
        self.status_label.pack(side=tk.LEFT, padx=8)
        
        # Credits - by Ajmal
        credits_label = tk.Label(
            status_frame,
            text="by Ajmal",
            font=("Segoe UI", 9),
            fg=self.text_secondary,
            bg=self.surface_color,
            anchor="center"
        )
        credits_label.pack(side=tk.LEFT, expand=True)
        
        # Character count - Cursor style
        self.char_count_label = tk.Label(
            status_frame,
            text="0 characters",
            font=("Segoe UI", 10),
            fg=self.text_secondary,
            bg=self.surface_color,
            anchor="e"
        )
        self.char_count_label.pack(side=tk.RIGHT, padx=8)
        
        # Update character count on text change
        self.text_input.bind('<KeyRelease>', self.update_char_count)
        self.text_input.bind('<Button-1>', self.update_char_count)
        
        # Initial character count
        self.update_char_count()
        
    def create_round_button(self, parent, text, command, bg_color, hover_color=None, width=None):
        """Create smooth, rounded window control button"""
        if hover_color is None:
            hover_color = self.button_hover
        
        # Smooth rounded buttons with padding
        size = width if width else 46
        height = 32
        corner_radius = 6  # Rounded corners
        
        btn_frame = tk.Frame(parent, bg=self.title_bar_bg, width=size, height=height)
        btn_frame.pack_propagate(False)
        
        canvas = tk.Canvas(
            btn_frame,
            width=size,
            height=height,
            bg=self.title_bar_bg,
            highlightthickness=0,
            relief=tk.FLAT,
            cursor="hand2"
        )
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Store text as attribute for dynamic updates
        canvas.button_text = text
        canvas.current_color = bg_color
        
        def draw_button(text_color, btn_text=None):
            if btn_text is None:
                btn_text = canvas.button_text
            canvas.delete("all")
            
            # Only draw the symbol, no background/outline
            # Draw text centered with specified color
            # Use smaller font for "SS" (two characters)
            font_size = 10 if len(btn_text) > 1 else 13
            canvas.create_text(
                size // 2, height // 2,
                text=btn_text,
                fill=text_color,
                font=("Segoe UI", font_size, "normal")
            )
        
        draw_button(self.text_color)
        
        # Smooth hover effects - change text color on hover
        def on_enter(e):
            # Use a lighter color for hover (or white)
            draw_button("#ffffff")
        
        def on_leave(e):
            draw_button(self.text_color)
        
        def on_click(e):
            command()
        
        canvas.bind("<Enter>", on_enter)
        canvas.bind("<Leave>", on_leave)
        canvas.bind("<Button-1>", on_click)
        
        # Store draw function for external updates
        canvas.draw_button = lambda color, text=None: draw_button(color, text)
        
        return btn_frame, canvas
    
    def start_drag(self, event):
        """Start dragging the window"""
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
    
    def on_drag(self, event):
        """Handle window dragging"""
        if not self.is_maximized:
            x = self.root.winfo_x() + event.x_root - self.drag_start_x
            y = self.root.winfo_y() + event.y_root - self.drag_start_y
            self.root.geometry(f"+{x}+{y}")
            self.drag_start_x = event.x_root
            self.drag_start_y = event.y_root
    
    def minimize_window(self):
        """Minimize the window"""
        self.root.overrideredirect(False)
        self.root.state('iconic')
        self.root.overrideredirect(True)
    
    def toggle_maximize(self):
        """Toggle maximize/restore window"""
        if self.is_maximized:
            # Restore
            if self.normal_geometry:
                self.root.geometry(self.normal_geometry)
            self.is_maximized = False
            self.maximize_btn_canvas.button_text = "□"
            self.maximize_btn_canvas.draw_button(self.text_color, "□")
        else:
            # Maximize
            self.normal_geometry = self.root.geometry()
            self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")
            self.is_maximized = True
            self.maximize_btn_canvas.button_text = "❐"
            self.maximize_btn_canvas.draw_button(self.text_color, "❐")
    
    def take_screenshot(self):
        """Take a screenshot by pressing Print Screen key"""
        try:
            self.keyboard_controller.press(Key.print_screen)
            self.keyboard_controller.release(Key.print_screen)
        except AttributeError:
            # Fallback: try using Windows API
            try:
                import ctypes
                ctypes.windll.user32.keybd_event(0x2C, 0, 0, 0)  # Print Screen down
                ctypes.windll.user32.keybd_event(0x2C, 0, 2, 0)  # Print Screen up
            except:
                pass
    
    def close_window(self):
        """Close the window"""
        self.on_closing()
        
    def update_char_count(self, event=None):
        content = self.text_input.get("1.0", tk.END)
        char_count = len(content.rstrip('\n'))
        self.char_count_label.config(text=f"{char_count} characters")
        
    def setup_hotkey(self):
        """Setup global hotkey listener"""
        def on_press(key):
            try:
                if key == self.hotkey_key:
                    if not self.hotkey_pressed and not self.is_typing:
                        self.hotkey_pressed = True
                        self.trigger_typing()
            except AttributeError:
                pass
                
        def on_release(key):
            try:
                if key == self.hotkey_key:
                    self.hotkey_pressed = False
            except AttributeError:
                pass
        
        self.hotkey_listener = keyboard.Listener(
            on_press=on_press,
            on_release=on_release
        )
        self.hotkey_listener.start()
        
    def trigger_typing(self):
        """Trigger typing in a separate thread"""
        if self.is_typing:
            return
            
        self.text_to_type = self.text_input.get("1.0", tk.END).rstrip('\n')
        if not self.text_to_type:
            self.update_status("No text to type")
            return
            
        self.is_typing = True
        self.update_status("Typing...")
        
        # Run typing in a separate thread to avoid blocking UI
        threading.Thread(target=self.type_text, daemon=True).start()
        
    def type_text(self):
        """Type text character by character"""
        # Small delay before starting to ensure hotkey is released
        time.sleep(0.2)
        
        try:
            in_exponent = False
            has_typed_digits = False  # Track if we've typed digits in the exponent
            paren_depth = 0  # Track parenthesis depth (even = no open pairs, odd = pair(s) open)
            i = 0
            text_list = list(self.text_to_type)
            # Characters that end an exponent
            exponent_end_chars = [' ', '+', '-', '*', '/', '=', '(', ')', '[', ']', '{', '}', ',', ';', '\n', '\t']
            
            while i < len(text_list):
                if not self.is_typing:
                    break
                
                char = text_list[i]
                is_last_char = (i == len(text_list) - 1)
                is_digit = char.isdigit()
                # Check next character
                has_next = (i + 1 < len(text_list))
                next_char = text_list[i + 1] if has_next else None
                next_is_digit = next_char.isdigit() if next_char else False
                
                # Detect start of exponent
                if char == '^' and not in_exponent:
                    in_exponent = True
                    has_typed_digits = False
                    self.type_character(char)
                    i += 1
                    time.sleep(0.05)
                    continue
                
                # If we're in an exponent
                if in_exponent:
                    # If current character is a digit
                    if is_digit:
                        self.type_character(char)
                        has_typed_digits = True
                        i += 1
                        time.sleep(0.05)
                        
                        # If next character is NOT a digit (or end of string), press right arrow
                        if not next_is_digit:
                            # Press right arrow to exit exponent mode
                            self.keyboard_controller.press(Key.right)
                            self.keyboard_controller.release(Key.right)
                            time.sleep(0.05)
                            
                            # Reset exponent state
                            in_exponent = False
                            has_typed_digits = False
                            # Continue to next iteration (don't increment i again)
                            continue
                    # If current character is not a digit
                    else:
                        # If we've already typed digits, we've already pressed right arrow
                        # Just continue typing normally (exponent mode already exited)
                        if has_typed_digits:
                            in_exponent = False
                            has_typed_digits = False
                        
                        # Check if exponent ends (ending character or last character)
                        if char in exponent_end_chars or is_last_char:
                            # Type the current character if it's part of exponent (not an ending char)
                            if is_last_char and char not in exponent_end_chars:
                                self.type_character(char)
                                time.sleep(0.05)
                            
                            # Press right arrow to exit exponent mode (if not already pressed)
                            if in_exponent:
                                self.keyboard_controller.press(Key.right)
                                self.keyboard_controller.release(Key.right)
                                time.sleep(0.05)
                            
                            # Reset exponent state
                            in_exponent = False
                            has_typed_digits = False
                            
                            # Type the ending character with parenthesis handling
                            if char in exponent_end_chars:
                                # Handle parenthesis tracking
                                if char == '(':
                                    paren_depth += 1
                                    self.type_character(char)
                                    time.sleep(0.05)
                                elif char == ')':
                                    # Before count becomes even, press right arrow 3 times
                                    # Current depth is odd, after decrement it will be even
                                    if paren_depth % 2 == 1:  # Current depth is odd
                                        # Press right arrow 3 times before typing closing parenthesis
                                        for _ in range(3):
                                            self.keyboard_controller.press(Key.right)
                                            self.keyboard_controller.release(Key.right)
                                            time.sleep(0.05)
                                    
                                    paren_depth -= 1
                                    self.type_character(char)
                                    time.sleep(0.05)
                                else:
                                    self.type_character(char)
                                    time.sleep(0.05)
                        else:
                            # Continue typing exponent characters (letters, etc.)
                            # Handle parenthesis tracking even in exponent
                            if char == '(':
                                paren_depth += 1
                                self.type_character(char)
                                time.sleep(0.05)
                            elif char == ')':
                                # Before count becomes even, press right arrow 3 times
                                # Current depth is odd, after decrement it will be even
                                if paren_depth % 2 == 1:  # Current depth is odd
                                    # Press right arrow 3 times before typing closing parenthesis
                                    for _ in range(3):
                                        self.keyboard_controller.press(Key.right)
                                        self.keyboard_controller.release(Key.right)
                                        time.sleep(0.05)
                                
                                paren_depth -= 1
                                self.type_character(char)
                                time.sleep(0.05)
                            else:
                                self.type_character(char)
                                time.sleep(0.05)
                else:
                    # Normal typing
                    # Handle parenthesis tracking
                    if char == '(':
                        paren_depth += 1
                        self.type_character(char)
                        time.sleep(0.05)
                    elif char == ')':
                        # Before count becomes even, press right arrow 3 times
                        # Current depth is odd, after decrement it will be even
                        if paren_depth % 2 == 1:  # Current depth is odd
                            # Press right arrow 3 times before typing closing parenthesis
                            for _ in range(3):
                                self.keyboard_controller.press(Key.right)
                                self.keyboard_controller.release(Key.right)
                                time.sleep(0.05)
                        
                        paren_depth -= 1
                        self.type_character(char)
                        time.sleep(0.05)
                    else:
                        self.type_character(char)
                        time.sleep(0.05)
                
                i += 1
            
            # If we're still in an exponent at the end, press right arrow
            if in_exponent:
                self.keyboard_controller.press(Key.right)
                self.keyboard_controller.release(Key.right)
                
            self.is_typing = False
            self.root.after(0, lambda: self.update_status("Completed"))
            time.sleep(1)
            self.root.after(0, lambda: self.update_status("Ready | Hotkey: `"))
            
        except Exception as e:
            self.is_typing = False
            self.root.after(0, lambda: self.update_status(f"Error: {str(e)}"))
            
    def type_character(self, char):
        """Type a single character using keyboard simulation"""
        if char == '\n':
            self.keyboard_controller.press(Key.enter)
            self.keyboard_controller.release(Key.enter)
        elif char == '\t':
            self.keyboard_controller.press(Key.tab)
            self.keyboard_controller.release(Key.tab)
        elif char == ' ':
            self.keyboard_controller.press(Key.space)
            self.keyboard_controller.release(Key.space)
        else:
            # For special characters, we need to handle them properly
            # Most characters can be typed directly
            try:
                self.keyboard_controller.type(char)
            except Exception:
                # Fallback: try to type as-is
                self.keyboard_controller.type(char)
                
    def update_status(self, message):
        """Update status label"""
        self.status_label.config(text=message)
        
    def on_closing(self):
        """Handle window closing"""
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = MathAutoTyper(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Center window on screen
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    # Force window to be visible first
    root.deiconify()
    root.update()
    
    # Apply window styling after window is fully created and visible
    def apply_styling():
        app.register_taskbar_window()
        app.apply_rounded_corners()
        root.update()
    
    root.after(200, apply_styling)
    
    root.mainloop()

if __name__ == "__main__":
    main()

