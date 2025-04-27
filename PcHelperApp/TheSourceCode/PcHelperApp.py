import tkinter as tk
from tkinter import messagebox, filedialog
import os
import shutil
import socket
import tempfile
import ctypes
import webbrowser
import threading
import pyperclip
import sqlite3
import queue
import time
import colorsys

# Install customtkinter if not already installed: pip install customtkinter
try:
    import customtkinter as ctk
    USE_CUSTOM_TKINTER = True
except ImportError:
    USE_CUSTOM_TKINTER = False

# Language translations
TRANSLATIONS = {
    'english': {
        'app_title': "PC Helper",
        'main_title': "PC Helper - Click any button below",
        'pc_tools': "🔧 PC Tools",
        'important_links': "🔗 Important Links",
        'change_background': {
            'title': "🖼️ Change Background",
            'desc': "Choose a new picture for your desktop"
        },
        'empty_trash': {
            'title': "🗑️ Empty Trash",
            'desc': "Clean up your recycle bin"
        },
        'check_internet': {
            'title': "🌐 Check Internet",
            'desc': "Test if your internet is working"
        },
        'clean_files': {
            'title': "🧹 Clean Files",
            'desc': "Remove temporary files to free up space"
        },
        'toggle_system_theme': {
            'title': "🌓 Toggle System Theme",
            'desc': "Switch between Light and Dark mode for the system"
        },
        'clipboard_history': {
            'title': "📋 Clipboard History",
            'desc': "View and manage clipboard entries"
        },
        'email_reminder': "📧 Don't forget to check your email!",
        'settings': "⚙️ Settings",
        'app_theme': "Toggle App Theme"
    },
    'arabic': {
        'app_title': "مساعد الكمبيوتر",
        'main_title': "مساعد الكمبيوتر - انقر فوق أي زر أدناه",
        'pc_tools': "🔧 أدوات الكمبيوتر",
        'important_links': "🔗 روابط مهمة",
        'change_background': {
            'title': "🖼️ تغيير الخلفية",
            'desc': "اختر صورة جديدة لسطح المكتب"
        },
        'empty_trash': {
            'title': "🗑️ إفراغ سلة المحذوفات",
            'desc': "تنظيف سلة المحذوفات"
        },
        'check_internet': {
            'title': "🌐 فحص الإنترنت",
            'desc': "اختبار اتصال الإنترنت"
        },
        'clean_files': {
            'title': "🧹 تنظيف الملفات",
            'desc': "إزالة الملفات المؤقتة لتحرير المساحة"
        },
        'toggle_system_theme': {
            'title': "🌓 تبديل مظهر النظام",
            'desc': "التبديل بين الوضع الفاتح والداكن للنظام"
        },
        'clipboard_history': {
            'title': "📋 سجل الحافظة",
            'desc': "عرض وإدارة محتويات الحافظة"
        },
        'email_reminder': "📧 لا تنس التحقق من بريدك الإلكتروني!",
        'settings': "⚙️ الإعدادات",
        'app_theme': "تبديل مظهر التطبيق"
    }
}

# Modern color palette - eye-friendly
COLORS = {
    'light': {
        'primary': "#4361ee",         # Primary blue
        'secondary': "#3a0ca3",       # Deep purple
        'success': "#4cc9f0",         # Light blue
        'warning': "#f72585",         # Pink
        'info': "#4895ef",            # Medium blue
        'danger': "#f94144",          # Red
        'light': "#f8f9fa",           # Light gray
        'dark': "#212529",            # Dark gray
        'background': "#f8f9fa",      # Light background
        'card_bg': "#ffffff",         # Card background
        'text': "#212529",            # Text color
        'title': "#3a0ca3",           # Title color
        'button_text': "#ffffff"      # Button text
    },
    'dark': {
        'primary': "#4361ee",         # Primary blue
        'secondary': "#7209b7",       # Vibrant purple
        'success': "#4cc9f0",         # Light blue
        'warning': "#f72585",         # Pink
        'info': "#4895ef",            # Medium blue
        'danger': "#f94144",          # Red
        'light': "#e9ecef",           # Light gray
        'dark': "#212529",            # Dark gray
        'background': "#121212",      # Dark background
        'card_bg': "#1e1e1e",         # Card background
        'text': "#e9ecef",            # Text color
        'title': "#4cc9f0",           # Title color
        'button_text': "#ffffff"      # Button text
    }
}

class ClipboardHistoryManager:
    def __init__(self, max_entries=50):
        self.db_path = 'clipboard_history.db'
        self.max_entries = max_entries
        self.action_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.last_content = ""
        self.start_db_thread()

    def start_db_thread(self):
        def db_worker():
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            
            while True:
                action, args = self.action_queue.get()
                if action == 'stop':
                    conn.close()
                    break
                
                try:
                    if action == 'add':
                        content = args[0]
                        cursor = conn.cursor()
                        cursor.execute('INSERT INTO history (content) VALUES (?)', (content,))
                        
                        # Trim history
                        cursor.execute(f'''
                            DELETE FROM history WHERE id NOT IN (
                                SELECT id FROM history ORDER BY timestamp DESC LIMIT {self.max_entries}
                            )
                        ''')
                        conn.commit()
                        self.result_queue.put(True)
                    
                    elif action == 'get':
                        cursor = conn.cursor()
                        cursor.execute('SELECT content FROM history ORDER BY timestamp DESC')
                        results = [item[0] for item in cursor.fetchall()]
                        self.result_queue.put(results)
                    
                    elif action == 'clear':
                        cursor = conn.cursor()
                        cursor.execute('DELETE FROM history')
                        conn.commit()
                        self.result_queue.put("Clipboard history cleared!")
                
                except sqlite3.Error as e:
                    self.result_queue.put(f"Database error: {str(e)}")
                
                self.action_queue.task_done()
        
        self.db_thread = threading.Thread(target=db_worker, daemon=True)
        self.db_thread.start()

    def add_to_history(self, content):
        if content and content != self.last_content:
            self.last_content = content
            self.action_queue.put(('add', (content,)))
            return self.result_queue.get()
        return False

    def get_history(self):
        self.action_queue.put(('get', ()))
        return self.result_queue.get()

    def clear_history(self):
        self.action_queue.put(('clear', ()))
        return self.result_queue.get()

    def __del__(self):
        self.action_queue.put(('stop', ()))
        self.db_thread.join()

class PCHelperApp:
    def __init__(self, root):
        self.root = root
        self.current_language = 'english'
        self.dark_mode = False
        self.current_theme = 'light'
        self.color_scheme = COLORS[self.current_theme]
        
        if USE_CUSTOM_TKINTER:
            ctk.set_appearance_mode("light")
            ctk.set_default_color_theme("blue")
        
        self.setup_ui()
        self.clipboard_manager = ClipboardHistoryManager()
        self.start_clipboard_monitoring()
        self.show_email_reminder()

    def setup_ui(self):
        self.root.title(TRANSLATIONS[self.current_language]['app_title'])
        self.root.geometry("1000x800")
        self.root.minsize(800, 600)
        
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.create_menu()

        if USE_CUSTOM_TKINTER:
            self.main_frame = ctk.CTkFrame(self.root, fg_color=self.color_scheme['background'])
        else:
            self.main_frame = tk.Frame(self.root, bg=self.color_scheme['background'])
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        if USE_CUSTOM_TKINTER:
            self.header_frame = ctk.CTkFrame(self.main_frame, fg_color=self.color_scheme['primary'], height=80, corner_radius=0)
        else:
            self.header_frame = tk.Frame(self.main_frame, bg=self.color_scheme['primary'], height=80)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 10))
        
        if USE_CUSTOM_TKINTER:
            self.main_title_label = ctk.CTkLabel(
                self.header_frame,
                text=TRANSLATIONS[self.current_language]['main_title'],
                font=ctk.CTkFont(family="Arial", size=24, weight="bold"),
                text_color=self.color_scheme['button_text'],
                pady=20
            )
        else:
            self.main_title_label = tk.Label(
                self.header_frame,
                text=TRANSLATIONS[self.current_language]['main_title'],
                font=("Arial", 24, "bold"),
                fg=self.color_scheme['button_text'],
                bg=self.color_scheme['primary'],
                pady=20
            )
        self.main_title_label.pack(pady=15)

        if USE_CUSTOM_TKINTER:
            self.content_frame = ctk.CTkScrollableFrame(
                self.main_frame,
                fg_color=self.color_scheme['background']
            )
            self.content_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
            self.content_frame.grid_columnconfigure(0, weight=1)
        else:
            canvas = tk.Canvas(self.main_frame, bg=self.color_scheme['background'], highlightthickness=0)
            scrollbar = tk.Scrollbar(self.main_frame, orient="vertical", command=canvas.yview)
            self.content_frame = tk.Frame(canvas, bg=self.color_scheme['background'])
            
            self.content_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
            scrollbar.grid(row=1, column=1, sticky="ns")

        self.update_ui()

    def create_menu(self):
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)
        
        language_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Language", menu=language_menu)
        language_menu.add_command(label="English", command=lambda: self.change_language('english'))
        language_menu.add_command(label="العربية", command=lambda: self.change_language('arabic'))

        settings_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label=TRANSLATIONS[self.current_language]['settings'], menu=settings_menu)
        settings_menu.add_command(
            label=TRANSLATIONS[self.current_language]['app_theme'],
            command=self.toggle_app_theme
        )

    def toggle_app_theme(self):
        self.dark_mode = not self.dark_mode
        self.current_theme = 'dark' if self.dark_mode else 'light'
        self.color_scheme = COLORS[self.current_theme]
        
        if USE_CUSTOM_TKINTER:
            ctk.set_appearance_mode("dark" if self.dark_mode else "light")
        
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        self.setup_ui()

    def toggle_system_theme(self):
        try:
            current_theme = ctypes.windll.dwmapi.DwmGetWindowAttribute(0, 20)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(0, 20, not current_theme)
            self.show_notification("System Theme", "System theme has been toggled!")
        except Exception:
            self.show_notification("Error", "Could not toggle system theme. Please try again.", error=True)

    def show_notification(self, title, message, error=False):
        if USE_CUSTOM_TKINTER:
            notification = ctk.CTkToplevel(self.root)
            notification.title("")
            notification.geometry("400x150")
            notification.attributes('-topmost', True)
            notification.resizable(False, False)
            notification.overrideredirect(True)
            
            notification.update_idletasks()
            width = notification.winfo_width()
            height = notification.winfo_height()
            x = (notification.winfo_screenwidth() // 2) - (width // 2)
            y = (notification.winfo_screenheight() // 2) - (height // 2)
            notification.geometry(f'{width}x{height}+{x}+{y}')
            
            color = self.color_scheme['danger'] if error else self.color_scheme['success']
            notification.configure(fg_color=color)
            
            frame = ctk.CTkFrame(notification, fg_color=color, corner_radius=10, border_width=0)
            frame.pack(fill="both", expand=True, padx=2, pady=2)
            
            title_label = ctk.CTkLabel(
                frame,
                text=title,
                font=ctk.CTkFont(family="Arial", size=16, weight="bold"),
                text_color=self.color_scheme['button_text']
            )
            title_label.pack(pady=(15, 5))
            
            message_label = ctk.CTkLabel(
                frame,
                text=message,
                font=ctk.CTkFont(family="Arial", size=14),
                text_color=self.color_scheme['button_text']
            )
            message_label.pack(pady=5)
            
            close_button = ctk.CTkButton(
                frame,
                text="Got it",
                command=notification.destroy,
                fg_color=self._adjust_color(color, -15),
                hover_color=self._adjust_color(color, -30),
                text_color=self.color_scheme['button_text'],
                height=30,
                width=100,
                corner_radius=15
            )
            close_button.pack(pady=15)
            
            notification.after(3000, notification.destroy)
        else:
            if error:
                messagebox.showerror(title, message)
            else:
                messagebox.showinfo(title, message)

    def show_email_reminder(self):
        if USE_CUSTOM_TKINTER:
            reminder_window = ctk.CTkToplevel(self.root)
            reminder_window.title("")
            reminder_window.geometry("400x200")
            reminder_window.attributes('-topmost', True)
            reminder_window.overrideredirect(True)
            
            reminder_window.update_idletasks()
            width = reminder_window.winfo_width()
            height = reminder_window.winfo_height()
            x = (reminder_window.winfo_screenwidth() // 2) - (width // 2)
            y = (reminder_window.winfo_screenheight() // 2) - (height // 2)
            reminder_window.geometry(f'{width}x{height}+{x}+{y}')
            
            frame = ctk.CTkFrame(
                reminder_window,
                corner_radius=15,
                fg_color=self.color_scheme['primary'],
                border_width=0
            )
            frame.pack(fill="both", expand=True, padx=2, pady=2)
            
            reminder_label = ctk.CTkLabel(
                frame,
                text=TRANSLATIONS[self.current_language]['email_reminder'],
                font=ctk.CTkFont(family="Arial", size=18, weight="bold"),
                text_color=self.color_scheme['button_text']
            )
            reminder_label.pack(pady=40)
            
            close_button = ctk.CTkButton(
                frame,
                text="Got it!",
                command=reminder_window.destroy,
                fg_color=self._adjust_color(self.color_scheme['primary'], -15),
                hover_color=self._adjust_color(self.color_scheme['primary'], -30),
                text_color=self.color_scheme['button_text'],
                height=40,
                width=120,
                corner_radius=20,
                font=ctk.CTkFont(family="Arial", size=14, weight="bold")
            )
            close_button.pack(pady=20)
            
            reminder_window.attributes('-alpha', 0.0)
            
            def fade_in(alpha):
                alpha += 0.1
                reminder_window.attributes('-alpha', alpha)
                if alpha < 1.0:
                    reminder_window.after(30, lambda: fade_in(alpha))
            
            reminder_window.after(10, lambda: fade_in(0.0))
        else:
            messagebox.showinfo("Reminder", TRANSLATIONS[self.current_language]['email_reminder'])

    def change_language(self, language):
        self.current_language = language
        self.update_ui()

    def update_ui(self):
        if self.main_title_label:
            if USE_CUSTOM_TKINTER:
                self.main_title_label.configure(text=TRANSLATIONS[self.current_language]['main_title'])
            else:
                self.main_title_label.config(text=TRANSLATIONS[self.current_language]['main_title'])
        
        self.root.title(TRANSLATIONS[self.current_language]['app_title'])

        for widget in self.content_frame.winfo_children():
            widget.destroy()

        self.create_section(
            TRANSLATIONS[self.current_language]['pc_tools'],
            [
                (TRANSLATIONS[self.current_language]['change_background']['title'],
                 TRANSLATIONS[self.current_language]['change_background']['desc'],
                 self.color_scheme['primary'], self.change_background),
                (TRANSLATIONS[self.current_language]['empty_trash']['title'],
                 TRANSLATIONS[self.current_language]['empty_trash']['desc'],
                 self.color_scheme['success'], self.empty_trash),
                (TRANSLATIONS[self.current_language]['check_internet']['title'],
                 TRANSLATIONS[self.current_language]['check_internet']['desc'],
                 self.color_scheme['info'], self.check_internet),
                (TRANSLATIONS[self.current_language]['clean_files']['title'],
                 TRANSLATIONS[self.current_language]['clean_files']['desc'],
                 self.color_scheme['warning'], self.clean_temp_files),
                (TRANSLATIONS[self.current_language]['toggle_system_theme']['title'],
                 TRANSLATIONS[self.current_language]['toggle_system_theme']['desc'],
                 self.color_scheme['secondary'], self.toggle_system_theme),
                (TRANSLATIONS[self.current_language]['clipboard_history']['title'],
                 TRANSLATIONS[self.current_language]['clipboard_history']['desc'],
                 self.color_scheme['info'], self.show_clipboard_history)
            ]
        )

        self.create_section(
            TRANSLATIONS[self.current_language]['important_links'],
            [
                ("▶️ YouTube", "", "#FF0000", lambda: self.open_website("https://www.youtube.com")),
                ("📘 Facebook", "", "#4267B2", lambda: self.open_website("https://www.facebook.com")),
                ("🐦 Twitter", "", "#1DA1F2", lambda: self.open_website("https://www.twitter.com")),
            ],
            link_buttons=True
        )

    def create_section(self, title, items, link_buttons=False):
        if USE_CUSTOM_TKINTER:
            section_frame = ctk.CTkFrame(
                self.content_frame,
                fg_color=self.color_scheme['card_bg'],
                corner_radius=15,
                border_width=0
            )
        else:
            section_frame = tk.Frame(
                self.content_frame,
                bg=self.color_scheme['card_bg'],
                bd=0,
                highlightthickness=0
            )
        section_frame.pack(fill='x', padx=10, pady=15, ipady=10)
        
        if USE_CUSTOM_TKINTER:
            title_frame = ctk.CTkFrame(
                section_frame,
                fg_color=self.color_scheme['primary'], 
                height=40,
                corner_radius=10
            )
        else:
            title_frame = tk.Frame(
                section_frame,
                bg=self.color_scheme['primary'],
                height=40
            )
        title_frame.pack(fill='x', padx=10, pady=(10, 15))
        
        if USE_CUSTOM_TKINTER:
            title_label = ctk.CTkLabel(
                title_frame,
                text=title,
                font=ctk.CTkFont(family="Arial", size=18, weight="bold"),
                text_color=self.color_scheme['button_text']
            )
        else:
            title_label = tk.Label(
                title_frame,
                text=title,
                font=("Arial", 18, "bold"),
                fg=self.color_scheme['button_text'],
                bg=self.color_scheme['primary']
            )
        title_label.pack(pady=8)

        if USE_CUSTOM_TKINTER:
            content_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
        else:
            content_frame = tk.Frame(section_frame, bg=self.color_scheme['card_bg'])
        content_frame.pack(fill='x', padx=15, pady=10)
        
        rows = 3 if not link_buttons else 1
        cols = 2 if not link_buttons else 3
        
        for i in range(cols):
            content_frame.grid_columnconfigure(i, weight=1, uniform="column")
        
        if link_buttons:
            for i, (text, _, color, command) in enumerate(items):
                self.create_link_button(content_frame, text, color, command, col=i, row=0)
        else:
            for i, (text, desc, color, command) in enumerate(items):
                row = i // cols
                col = i % cols
                self.create_helper_button(content_frame, text, desc, color, command, col=col, row=row)

    def create_helper_button(self, parent, title, description, color, command, col, row):
        if USE_CUSTOM_TKINTER:
            button_frame = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=12)
            button_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            
            button = ctk.CTkButton(
                button_frame,
                text="",
                fg_color=color,
                hover_color=self._adjust_color(color, -15),
                corner_radius=12,
                height=125,
                command=lambda: self.run_in_thread(command)
            )
            button.grid(row=0, column=0, sticky="nsew")
            
            title_label = ctk.CTkLabel(
                button,
                text=title,
                font=ctk.CTkFont(family="Arial", size=16, weight="bold"),
                text_color=self.color_scheme['button_text']
            )
            title_label.grid(row=0, column=0, pady=(20, 5), sticky="n")
            
            desc_label = ctk.CTkLabel(
                button,
                text=description,
                font=ctk.CTkFont(family="Arial", size=12),
                text_color=self.color_scheme['button_text']
            )
            desc_label.grid(row=1, column=0, pady=(0, 15), sticky="n")
            
            button_frame.grid_rowconfigure(0, weight=1)
            button_frame.grid_columnconfigure(0, weight=1)
            button.grid_rowconfigure(0, weight=1)
            button.grid_rowconfigure(1, weight=1)
            button.grid_columnconfigure(0, weight=1)
        else:
            button_frame = tk.Frame(parent, bg=self.color_scheme['card_bg'])
            button_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            
            button = tk.Button(
                button_frame,
                text=f"{title}\n{description}",
                bg=color,
                fg=self.color_scheme['button_text'],
                activebackground=self._adjust_color(color, -15),
                activeforeground=self.color_scheme['button_text'],
                relief="flat",
                height=8,
                width=30,
                wraplength=180,
                font=("Arial", 10, "bold"),
                command=lambda: self.run_in_thread(command)
            )
            button.pack(fill="both", expand=True)

    def create_link_button(self, parent, title, color, command, col, row):
        if USE_CUSTOM_TKINTER:
            button = ctk.CTkButton(
                parent,
                text=title,
                font=ctk.CTkFont(family="Arial", size=14, weight="bold"),
                fg_color=color,
                hover_color=self._adjust_color(color, -15),
                text_color="white",
                corner_radius=20,
                height=40,
                command=command
            )
            button.grid(row=row, column=col, padx=10, pady=10, sticky="ew")
        else:
            button = tk.Button(
                parent,
                text=title,
                bg=color,
                fg="white",
                activebackground=self._adjust_color(color, -15),
                activeforeground="white",
                relief="flat",
                height=2,
                width=15,
                font=("Arial", 10, "bold"),
                command=command
            )
            button.grid(row=row, column=col, padx=10, pady=10, sticky="ew")

    def _adjust_color(self, color, amount):
        try:
            color = color.lstrip('#')
            rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
            h, s, v = colorsys.rgb_to_hsv(rgb[0]/255, rgb[1]/255, rgb[2]/255)
            v = max(0, min(1, v + amount/100))
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
        except Exception:
            return color

    def show_clipboard_history(self):
        history = self.clipboard_manager.get_history()
        
        if USE_CUSTOM_TKINTER:
            history_window = ctk.CTkToplevel(self.root)
            history_window.title("Clipboard History")
            history_window.geometry("700x500")
            history_window.minsize(600, 400)
            history_window.configure(fg_color=self.color_scheme['background'])
            
            header_frame = ctk.CTkFrame(
                history_window,
                fg_color=self.color_scheme['primary'], 
                height=60,
                corner_radius=0
            )
            header_frame.pack(fill='x', pady=(0, 15))
            
            header_label = ctk.CTkLabel(
                header_frame,
                text="Clipboard History",
                font=ctk.CTkFont(family="Arial", size=20, weight="bold"),
                text_color=self.color_scheme['button_text']
            )
            header_label.pack(pady=15)
            
            content_frame = ctk.CTkFrame(
                history_window,
                fg_color=self.color_scheme['background']
            )
            content_frame.pack(fill='both', expand=True, padx=15, pady=0)
            
            search_frame = ctk.CTkFrame(
                content_frame,
                fg_color=self.color_scheme['card_bg'],
                corner_radius=10
            )
            search_frame.pack(pady=10, padx=10, fill='x')

            search_entry = ctk.CTkEntry(
                search_frame,
                placeholder_text="Search in clipboard history...",
                border_width=0,
                height=36,
                corner_radius=8,
                font=ctk.CTkFont(family="Arial", size=12)
            )
            search_entry.pack(side='left', padx=10, fill='x', expand=True)


            def filter_history():
                query = search_entry.get().lower()
                history_list.delete(0, tk.END)
                for i, item in enumerate(history, 1):
                    if query in item.lower():
                        display_text = item.strip()
                        if len(display_text) > 80:
                            display_text = display_text[:80] + "..."
                        history_list.insert(tk.END, f"{i}. {display_text}")
                        if i % 2 == 0:
                            history_list.itemconfig(i-1, {'bg': self._adjust_color(self.color_scheme['card_bg'], -5)})
                        else:
                            history_list.itemconfig(i-1, {'bg': self.color_scheme['card_bg']})

            search_button = ctk.CTkButton(
                search_frame,
                text="Search",
                command=filter_history,
                fg_color=self.color_scheme['primary'],
                hover_color=self._adjust_color(self.color_scheme['primary'], -15),
                corner_radius=8,
                width=100,
                height=36,
                font=ctk.CTkFont(family="Arial", size=12, weight="bold")
            )
            search_button.pack(side='right', padx=10)

            list_frame = ctk.CTkFrame(
                content_frame,
                fg_color=self.color_scheme['card_bg'],
                corner_radius=10
            )
            list_frame.pack(padx=10, pady=10, fill='both', expand=True)

            if self.dark_mode:
                list_bg = self.color_scheme['card_bg']
                list_fg = self.color_scheme['text']
                select_bg = self.color_scheme['primary']
                select_fg = self.color_scheme['button_text']
            else:
                list_bg = self.color_scheme['card_bg']
                list_fg = self.color_scheme['text']
                select_bg = self.color_scheme['primary']
                select_fg = self.color_scheme['button_text']

            history_list = tk.Listbox(
                list_frame,
                font=("Arial", 11),
                bg=list_bg,
                fg=list_fg,
                selectbackground=select_bg,
                selectforeground=select_fg,
                relief="flat",
                highlightthickness=0,
                borderwidth=0
            )
            history_list.pack(side="left", padx=5, pady=5, fill='both', expand=True)

            list_scrollbar = ctk.CTkScrollbar(
                list_frame,
                command=history_list.yview,
                button_color=self.color_scheme['primary'],
                button_hover_color=self.color_scheme['secondary']
            )
            list_scrollbar.pack(side="right", fill="y")
            history_list.config(yscrollcommand=list_scrollbar.set)

            for i, item in enumerate(history, 1):
                display_text = item.strip()
                if len(display_text) > 80:
                    display_text = display_text[:80] + "..."
                history_list.insert(tk.END, f"{i}. {display_text}")
                if i % 2 == 0:
                    history_list.itemconfig(i-1, {'bg': self._adjust_color(self.color_scheme['card_bg'], -5)})

            preview_frame = ctk.CTkFrame(
                content_frame,
                fg_color=self.color_scheme['card_bg'],
                corner_radius=10,
                height=100
            )
            preview_frame.pack(padx=10, pady=(10, 0), fill='x')

            preview_label = ctk.CTkLabel(
                preview_frame,
                text="Select an item to preview",
                font=ctk.CTkFont(family="Arial", size=12),
                wraplength=650
            )
            preview_label.pack(padx=10, pady=10)

            def on_select(event):
                try:
                    selection = history_list.curselection()
                    if selection:
                        index = selection[0]
                        preview_label.configure(text=history[index])
                except Exception:
                    pass

            history_list.bind('<<ListboxSelect>>', on_select)

            button_frame = ctk.CTkFrame(
                content_frame,
                fg_color="transparent",
                height=50
            )
            button_frame.pack(pady=15, padx=10, fill='x')

            def copy_selected():
                selection = history_list.curselection()
                if selection:
                    index = selection[0]
                    pyperclip.copy(history[index])
                    self.show_notification("Clipboard", f"Copied item to clipboard", error=False)

            def clear_history():
                result = self.clipboard_manager.clear_history()
                self.show_notification("Clipboard", result, error=False)
                history_window.destroy()

            copy_button = ctk.CTkButton(
                button_frame,
                text="Copy Selected",
                command=copy_selected,
                fg_color=self.color_scheme['info'],
                hover_color=self._adjust_color(self.color_scheme['info'], -15),
                corner_radius=10,
                height=40,
                width=150,
                font=ctk.CTkFont(family="Arial", size=13, weight="bold")
            )
            copy_button.pack(side='left', padx=10)

            clear_button = ctk.CTkButton(
                button_frame,
                text="Clear History",
                command=clear_history,
                fg_color=self.color_scheme['danger'],
                hover_color=self._adjust_color(self.color_scheme['danger'], -15),
                corner_radius=10,
                height=40,
                width=150,
                font=ctk.CTkFont(family="Arial", size=13, weight="bold")
            )
            clear_button.pack(side='right', padx=10)

            close_button = ctk.CTkButton(
                button_frame,
                text="Close",
                command=history_window.destroy,
                fg_color=self.color_scheme['secondary'],
                hover_color=self._adjust_color(self.color_scheme['secondary'], -15),
                corner_radius=10,
                height=40,
                width=100,
                font=ctk.CTkFont(family="Arial", size=13, weight="bold")
            )
            close_button.pack(side='bottom', padx=10)
        else:
            history_window = tk.Toplevel(self.root)
            history_window.title("Clipboard History")
            history_window.geometry("700x500")
            history_window.minsize(600, 400)
            
            listbox = tk.Listbox(
                history_window,
                font=("Arial", 12),
                selectmode=tk.SINGLE
            )
            listbox.pack(fill="both", expand=True, padx=10, pady=10)
            
            for i, item in enumerate(history, 1):
                display_text = item.strip()
                if len(display_text) > 80:
                    display_text = display_text[:80] + "..."
                listbox.insert(tk.END, f"{i}. {display_text}")
            
            button_frame = tk.Frame(history_window)
            button_frame.pack(fill="x", padx=10, pady=10)
            
            def copy_selected():
                selection = listbox.curselection()
                if selection:
                    index = selection[0]
                    pyperclip.copy(history[index])
                    messagebox.showinfo("Clipboard", "Copied item to clipboard")
            
            copy_button = tk.Button(
                button_frame,
                text="Copy Selected",
                command=copy_selected,
                bg=self.color_scheme['info'],
                fg="white",
                font=("Arial", 10, "bold")
            )
            copy_button.pack(side="left", padx=5)
            
            def clear_history():
                result = self.clipboard_manager.clear_history()
                messagebox.showinfo("Clipboard", result)
                history_window.destroy()
            
            clear_button = tk.Button(
                button_frame,
                text="Clear History",
                command=clear_history,
                bg=self.color_scheme['danger'],
                fg="white",
                font=("Arial", 10, "bold")
            )
            clear_button.pack(side="right", padx=5)
            
            close_button = tk.Button(
                button_frame,
                text="Close",
                command=history_window.destroy,
                bg=self.color_scheme['secondary'],
                fg="white",
                font=("Arial", 10, "bold")
            )
            close_button.pack(side="right", padx=5)

    def start_clipboard_monitoring(self):
        def monitor_clipboard():
            while True:
                try:
                    clipboard_content = pyperclip.paste()
                    if clipboard_content:
                        self.clipboard_manager.add_to_history(clipboard_content)
                    time.sleep(1)
                except Exception as e:
                    print(f"Clipboard monitoring error: {e}")
                    break

        threading.Thread(target=monitor_clipboard, daemon=True).start()

    def open_website(self, url):
        try:
            webbrowser.open(url)
        except Exception:
            self.show_notification("Error", f"Could not open {url}. Please try again.", error=True)

    def change_background(self):
        file_path = filedialog.askopenfilename(
            title="Choose a picture for your background",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
        )
        if file_path:
            try:
                ctypes.windll.user32.SystemParametersInfoW(20, 0, file_path, 3)
                self.show_notification("Success", "Your background has been changed!")
            except Exception:
                self.show_notification("Error", "Could not change background. Please try again.", error=True)

    def empty_trash(self):
        try:
            if os.name == 'nt':  # Windows
                os.system('rd /s /q c:\\$Recycle.bin')
            else:
                os.system('rm -rf ~/.local/share/Trash/*')
            self.show_notification("Success", "Your trash has been emptied!")
        except Exception:
            self.show_notification("Error", "Could not empty trash. Please try again.", error=True)

    def check_internet(self):
        try:
            if USE_CUSTOM_TKINTER:
                checking_notification = ctk.CTkToplevel(self.root)
                checking_notification.title("")
                checking_notification.geometry("300x100")
                checking_notification.attributes('-topmost', True)
                checking_notification.overrideredirect(True)
                
                checking_notification.update_idletasks()
                width = checking_notification.winfo_width()
                height = checking_notification.winfo_height()
                x = (checking_notification.winfo_screenwidth() // 2) - (width // 2)
                y = (checking_notification.winfo_screenheight() // 2) - (height // 2)
                checking_notification.geometry(f'{width}x{height}+{x}+{y}')
                
                checking_notification.configure(fg_color=self.color_scheme['info'])
                
                checking_label = ctk.CTkLabel(
                    checking_notification,
                    text="Checking your internet connection...",
                    font=ctk.CTkFont(family="Arial", size=14, weight="bold"),
                    text_color=self.color_scheme['button_text']
                )
                checking_label.pack(pady=30)
            else:
                checking_notification = tk.Toplevel(self.root)
                checking_notification.title("")
                checking_notification.geometry("300x100")
                checking_notification.attributes('-topmost', True)
                checking_notification.overrideredirect(True)
                
                checking_notification.update_idletasks()
                width = checking_notification.winfo_width()
                height = checking_notification.winfo_height()
                x = (checking_notification.winfo_screenwidth() // 2) - (width // 2)
                y = (checking_notification.winfo_screenheight() // 2) - (height // 2)
                checking_notification.geometry(f'{width}x{height}+{x}+{y}')
                
                checking_notification.configure(bg=self.color_scheme['info'])
                
                checking_label = tk.Label(
                    checking_notification,
                    text="Checking your internet connection...",
                    font=("Arial", 12, "bold"),
                    fg=self.color_scheme['button_text'],
                    bg=self.color_scheme['info']
                )
                checking_label.pack(pady=30)
            
            def check_connection():
                try:
                    socket.create_connection(("8.8.8.8", 53), timeout=3)
                    checking_notification.destroy()
                    self.show_notification("Success", "Your internet is working!")
                except OSError:
                    checking_notification.destroy()
                    self.show_notification("No Internet", "Please check your internet connection", error=True)
            
            threading.Thread(target=check_connection, daemon=True).start()
            
        except Exception:
            self.show_notification("Error", "Could not check internet connection", error=True)

    def clean_temp_files(self):
        try:
            if USE_CUSTOM_TKINTER:
                cleaning_notification = ctk.CTkToplevel(self.root)
                cleaning_notification.title("")
                cleaning_notification.geometry("300x100")
                cleaning_notification.attributes('-topmost', True)
                cleaning_notification.overrideredirect(True)
                
                cleaning_notification.update_idletasks()
                width = cleaning_notification.winfo_width()
                height = cleaning_notification.winfo_height()
                x = (cleaning_notification.winfo_screenwidth() // 2) - (width // 2)
                y = (cleaning_notification.winfo_screenheight() // 2) - (height // 2)
                cleaning_notification.geometry(f'{width}x{height}+{x}+{y}')
                
                cleaning_notification.configure(fg_color=self.color_scheme['warning'])
                
                cleaning_label = ctk.CTkLabel(
                    cleaning_notification,
                    text="Cleaning temporary files...",
                    font=ctk.CTkFont(family="Arial", size=14, weight="bold"),
                    text_color=self.color_scheme['button_text']
                )
                cleaning_label.pack(pady=30)
            else:
                cleaning_notification = tk.Toplevel(self.root)
                cleaning_notification.title("")
                cleaning_notification.geometry("300x100")
                cleaning_notification.attributes('-topmost', True)
                cleaning_notification.overrideredirect(True)
                
                cleaning_notification.update_idletasks()
                width = cleaning_notification.winfo_width()
                height = cleaning_notification.winfo_height()
                x = (cleaning_notification.winfo_screenwidth() // 2) - (width // 2)
                y = (cleaning_notification.winfo_screenheight() // 2) - (height // 2)
                cleaning_notification.geometry(f'{width}x{height}+{x}+{y}')
                
                cleaning_notification.configure(bg=self.color_scheme['warning'])
                
                cleaning_label = tk.Label(
                    cleaning_notification,
                    text="Cleaning temporary files...",
                    font=("Arial", 12, "bold"),
                    fg=self.color_scheme['button_text'],
                    bg=self.color_scheme['warning']
                )
                cleaning_label.pack(pady=30)
            
            def clean_temp():
                try:
                    temp_dir = tempfile.gettempdir()
                    files_removed = 0
                    
                    for item in os.listdir(temp_dir):
                        item_path = os.path.join(temp_dir, item)
                        try:
                            if os.path.isfile(item_path):
                                os.unlink(item_path)
                                files_removed += 1
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                                files_removed += 1
                        except Exception:
                            continue
                    
                    cleaning_notification.destroy()
                    self.show_notification("Success", f"Cleaned {files_removed} temporary files!")
                except Exception:
                    cleaning_notification.destroy()
                    self.show_notification("Error", "Could not clean all files. Please try again.", error=True)
            
            threading.Thread(target=clean_temp, daemon=True).start()
            
        except Exception:
            self.show_notification("Error", "Could not clean files. Please try again.", error=True)

    def run_in_thread(self, func):
        threading.Thread(target=func, daemon=True).start()


def main():
    if USE_CUSTOM_TKINTER:
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        root = ctk.CTk()
    else:
        root = tk.Tk()
        
    app = PCHelperApp(root)
    
    def on_closing():
        try:
            if hasattr(app, 'clipboard_manager'):
                app.clipboard_manager.__del__()
        except:
            pass
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'+{x}+{y}')
    
    root.mainloop()


if __name__ == "__main__":
    main()
