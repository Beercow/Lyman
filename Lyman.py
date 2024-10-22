import ast
import ctypes
import io
import json
import os
import re
import sys
import threading
import uuid
import webbrowser
import zlib

from PIL import Image, ImageTk
from dissect import cstruct
import keyboard
from screeninfo import get_monitors
import tkinter as tk
from tkinter import filedialog, font
from tkinter import ttk
from ttkthemes import ThemedTk

# Per monitor DPI aware. This app checks for the DPI when it is
# created and adjusts the scale factor whenever the DPI changes.
# These applications are not automatically scaled by the system.
ctypes.windll.shcore.SetProcessDpiAwareness(2)

# shortcuts to the WinAPI functionality
set_window_pos = ctypes.windll.user32.SetWindowPos
set_window_long = ctypes.windll.user32.SetWindowLongPtrW
get_window_long = ctypes.windll.user32.GetWindowLongPtrW
get_parent = ctypes.windll.user32.GetParent

# some of the WinAPI flags
GWL_STYLE = -16

WS_MINIMIZEBOX = 131072
WS_MAXIMIZEBOX = 65536

theme_data = None
__author__ = "Brian Maloney"
__version__ = "2024.06.11"
__email__ = "bmmaloney97@gmail.com"

if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app
    # path into variable _MEIPASS'.
    import pyi_splash

    def splash_loop():
        count = 0
        direction = 'right'
        while pyi_splash.is_alive():
            move = '\u0020' * count
            pyi_splash.update_text(f'{move}\u2588\u2588')
            if direction == 'right':
                if len(move) < 97:
                    count += 1
                else:
                    direction = 'left'
            else:
                if len(move) > 0:
                    count -= 1
                else:
                    direction = 'right'
            time.sleep(0.05)
    threading.Thread(target=splash_loop, daemon=True).start()
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

if os.path.isfile('lyman.settings'):
    with open("lyman.settings", "r") as jsonfile:
        theme_data = json.load(jsonfile)
        jsonfile.close()

if theme_data is None:
    theme_data = json.loads('{"theme": "vista"}')
    with open("lyman.settings", "w") as jsonfile:
        json.dump(theme_data, jsonfile)


class QuitDialog:
    def __init__(self, root):
        self.root = root
        self.create_dialog()

    def create_dialog(self):
        self.win = tk.Toplevel(self.root)
        self.setup_window()
        self.create_widgets()

    def setup_window(self):
        self.win.wm_transient(self.root)
        self.win.title("Please confirm")
        self.win.iconbitmap(application_path + '/Lyman/favicon.ico')
        self.win.grab_set()
        self.win.focus_force()
        self.win.resizable(False, False)
        self.win.protocol("WM_DELETE_WINDOW", self.__callback)

        self.sync_windows()

        self.root.bind('<Configure>', self.sync_windows)
        self.win.bind('<Configure>', self.sync_windows)

        self.setup_window_style()

    def setup_window_style(self):
        hwnd = get_parent(self.win.winfo_id())
        old_style = get_window_long(hwnd, GWL_STYLE)
        new_style = old_style & ~ WS_MAXIMIZEBOX & ~ WS_MINIMIZEBOX
        set_window_long(hwnd, GWL_STYLE, new_style)

    def create_widgets(self):
        self.frame = ttk.Frame(self.win, relief='flat')
        self.inner_frame = ttk.Frame(self.frame, relief='groove', padding=5)

        self.frame.grid(row=0, column=0)
        self.inner_frame.grid(row=0, column=0, padx=5, pady=5)

        self.label = ttk.Label(self.inner_frame,
                               text="Are you sure you want to exit?",
                               padding=5)
        self.yes = ttk.Button(self.inner_frame,
                              text="Yes",
                              takefocus=False,
                              command=self.btn1)
        self.no = ttk.Button(self.inner_frame,
                             text="No",
                             takefocus=False,
                             command=self.btn2)

        self.label.grid(row=0, column=0, columnspan=2)
        self.yes.grid(row=1, column=0, padx=5, pady=5)
        self.no.grid(row=1, column=1, padx=(0, 5), pady=5)

    def btn1(self):
        sys.exit()

    def btn2(self):
        self.root.unbind("<Configure>")
        self.win.destroy()

    def __callback(self):
        return

    def sync_windows(self, event=None):
        x = self.root.winfo_x()
        qw = self.win.winfo_width()
        y = self.root.winfo_y()
        qh = self.win.winfo_height()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        self.win.geometry("+%d+%d" % (x + w/2 - qw/2, y + h/2 - qh/2))


class Help:
    def __init__(self, root):
        self.root = root
        self.win = tk.Toplevel(self.root)
        self.win.title("Help")
        self.win.iconbitmap(application_path + '/Lyman/question.ico')
        self.win.focus_force()
        self.win.resizable(False, False)
        self.win.protocol("WM_DELETE_WINDOW", self.close_help)
        self.configure_window()

        self.frame = ttk.Frame(self.win)
        self.create_labels()

        self.frame.grid(row=0, column=0)
        self.place_labels()

    def configure_window(self):
        hwnd = get_parent(self.win.winfo_id())
        old_style = get_window_long(hwnd, GWL_STYLE)
        new_style = old_style & ~WS_MAXIMIZEBOX & ~WS_MINIMIZEBOX
        set_window_long(hwnd, GWL_STYLE, new_style)

    def create_labels(self):
        self.header_label = LabelSeparator(self.frame, text="Data types", width=15)

        self.label_texts = [
            "int8:    An 8-bit signed integer (1 byte).",
            "uint8:   An 8-bit unsigned integer (1 byte).",
            "int16:   A 16-bit signed integer (2 bytes).",
            "uint16:  A 16-bit unsigned integer (2 bytes).",
            "int32:   A 32-bit signed integer (4 bytes).",
            "uint32:  A 32-bit unsigned integer (4 bytes).",
            "int64:   A 64-bit signed integer (8 bytes).",
            "uint64:  A 64-bit unsigned integer (8 bytes).",
            "float16: A 16-bit floating-point number (2 bytes).",
            "float:   A 32-bit floating-point number (4 bytes).",
            "double:  A 64-bit floating-point number (8 bytes).",
            "char:    A single character (typically 8 bits).",
            "wchar:   A wide character (typically 16 or 32 bits).",
            "int24:   A 24-bit signed integer (3 bytes).",
            "uint24:  A 24-bit unsigned integer (3 bytes).",
            "int48:   A 48-bit signed integer (6 bytes).",
            "uint48:  A 48-bit unsigned integer (6 bytes).",
            "int128:  A 128-bit signed integer (16 bytes).",
            "uint128: A 128-bit unsigned integer (16 bytes).",
            "uleb128: Unsigned Little Endian Base 128 Varints (variable size).",
            "ileb128: Signed Little Endian Base 128 Varints (variable size).",
            "void:    A placeholder indicating no data type (usually used to represent absence of data type)."
        ]
        self.labels = [ttk.Label(self.frame, text=text, justify="left", font=('Consolas', 10, 'normal'), anchor='w') for text in self.label_texts]

    def place_labels(self):
        self.header_label.grid(row=0, column=0, pady=(5, 0), sticky="ew")
        for i, label in enumerate(self.labels):
            pady_top = 5 if i == 0 else 0
            pady_bottom = 20 if i == len(self.labels) - 1 else 0
            label.grid(row=i+1, column=0, padx=(10, 30),
                       pady=(pady_top, pady_bottom), sticky='w')

    def sync_windows(self, event=None):
        x = self.root.winfo_x()
        qw = self.win.winfo_width()
        y = self.root.winfo_y()
        qh = self.win.winfo_height()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        self.win.geometry("+%d+%d" % (x + w/2 - qw/2, y + h/2 - qh/2))

    def close_help(self):
        self.win.destroy()


class About:
    def __init__(self, root, parent):
        self.root = root
        self.parent = parent
        self.create_window()
        self.configure_window()
        self.create_widgets()

    def create_window(self):
        self.win = tk.Toplevel(self.root)
        self.win.wm_transient(self.root)
        self.win.title("About Lyman")
        self.win.iconbitmap(application_path + '/Lyman/favicon.ico')
        self.win.focus_force()
        self.win.resizable(False, False)
        self.win.protocol("WM_DELETE_WINDOW", self.close_about)

        self.sync_windows()

        self.root.bind('<Configure>', self.sync_windows)
        self.win.bind('<Configure>', self.sync_windows)

    def configure_window(self):
        hwnd = get_parent(self.win.winfo_id())
        old_style = get_window_long(hwnd, GWL_STYLE)
        new_style = old_style & ~WS_MAXIMIZEBOX & ~WS_MINIMIZEBOX
        set_window_long(hwnd, GWL_STYLE, new_style)

    def create_widgets(self):
        self.frame = ttk.Frame(self.win)
        self.label = ttk.Label(self.frame,
                               image=self.parent.lyman_img,
                               anchor='n')
        self.label1 = ttk.Label(self.frame,
                                text="Lyman",
                                justify="left",
                                anchor='w')
        self.label2 = ttk.Label(self.frame,
                                text=f"Version {__version__}",
                                justify="left",
                                anchor='w')
        self.label3 = ttk.Label(self.frame,
                                text=f"Copyright © {__version__[:4]}",
                                justify="left",
                                anchor='w')
        self.label4 = ttk.Label(self.frame,
                                text="Brian Maloney",
                                justify="left",
                                anchor='w')
        self.label5 = ttk.Label(self.frame,
                                text="L̲a̲t̲e̲s̲t̲_R̲e̲l̲e̲a̲s̲e̲",
                                foreground='#0563C1',
                                cursor="hand2",
                                justify="left",
                                anchor='w')
        self.text = tk.Text(self.frame,
                            width=27,
                            height=8,
                            wrap=tk.WORD)
        self.text.insert(tk.END, "GUI based application for developing cstruct files for OneDrive log entries.")
        self.text.config(state='disable')
        self.scrollbv = ttk.Scrollbar(self.frame,
                                      orient="vertical",
                                      command=self.text.yview)
        self.text.configure(yscrollcommand=self.scrollbv.set)
        self.ok = ttk.Button(self.frame,
                             text="OK",
                             takefocus=False,
                             command=self.close_about)

        self.bind_events()

        self.frame.grid(row=0, column=0)
        self.place_widgets()

    def bind_events(self):
        self.label5.bind("<Double-Button-1>", self.callback)

    def place_widgets(self):
        self.label.grid(row=0, column=0, rowspan=6,
                        padx=10, pady=(10, 0), sticky='n')
        self.label1.grid(row=0, column=1, padx=(0, 10),
                         pady=(10, 0), sticky='w')
        self.label2.grid(row=1, column=1, sticky='w')
        self.label3.grid(row=2, column=1, sticky='w')
        self.label4.grid(row=3, column=1, sticky='w')
        self.label5.grid(row=4, column=1, padx=(0, 10),
                         pady=(0, 10), sticky='w')
        self.text.grid(row=5, column=1, sticky='w')
        self.scrollbv.grid(row=5, column=2, padx=(0, 10), sticky="nsew")
        self.ok.grid(row=6, column=1, padx=(0, 10), pady=10, sticky='e')

    def sync_windows(self, event=None):
        try:
            x = self.root.winfo_x()
            qw = self.win.winfo_width()
            y = self.root.winfo_y()
            qh = self.win.winfo_height()
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            self.win.geometry("+%d+%d" % (x + w/2 - qw/2, y + h/2 - qh/2))
        except Exception:
            return

    def callback(self, event=None):
        webbrowser.open_new_tab("https://github.com/Beercow/Lyman/releases/latest")
        self.label5.configure(foreground='#954F72')

    def close_about(self):
        self.win.destroy()


class SearchFrame(ttk.Frame):
    def __init__(self, master, parent, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master
        self.parent = parent
        self.code_file_list = []
        self.function_dict = {}
        self.flags_dict = {}
        self.odl = tk.StringVar()
        self.cfv = tk.StringVar()
        self.funcv = tk.StringVar()
        self.flagsv = tk.StringVar()

        self.odl_file_label = ttk.Label(self, text="ODL:", takefocus=False)
        self.code_file_label = ttk.Label(self, text="Code_File:", takefocus=False)
        self.function_label = ttk.Label(self, text="Function:", takefocus=False)
        self.flags_label = ttk.Label(self, text="Flags:", takefocus=False)

        self.odl_frame = tk.Frame(self, takefocus=False, bg=ttk.Style().lookup('TFrame', 'background'))
        self.odl_file_entry = ttk.Entry(self.odl_frame, textvariable=self.odl)
        self.odl_button = ttk.Button(self, text="...", command=self.open_odl)
        self.code_frame = tk.Frame(self, takefocus=False, bg=ttk.Style().lookup('TFrame', 'background'))
        self.function_frame = tk.Frame(self, takefocus=False, bg=ttk.Style().lookup('TFrame', 'background'))
        self.flags_frame = tk.Frame(self, takefocus=False, bg=ttk.Style().lookup('TFrame', 'background'))


        self.code_file_entry = ttk.Combobox(self.code_frame,
                                            textvariable=self.cfv,
                                            width=53,
                                            state="disabled")
        self.function_entry = ttk.Combobox(self.function_frame,
                                           textvariable=self.funcv,
                                           width=129,
                                           state="disabled")
        self.flags_entry = ttk.Combobox(self.flags_frame,
                                        textvariable=self.flagsv,
                                        width=6,
                                        justify=tk.CENTER,
                                        state="disabled")

        self.search_button = ttk.Button(self,
                                        image=self.parent.search_img,
                                        command=self.retrieve_values,
                                        state="disabled")

        self.setup_layout()

    def setup_layout(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=0)
        self.grid_columnconfigure(3, weight=0)
        self.grid_columnconfigure(4, weight=0)
        self.grid_columnconfigure(5, weight=0)
        self.grid_columnconfigure(6, weight=1)
        self.odl_frame.grid_columnconfigure(0, weight=1)
        self.odl_file_label.grid(row=0, column=0, pady=5, sticky='e')
        self.odl_frame.grid(row=0, column=1, columnspan=4,
                            padx=5, pady=5, sticky='ew')
        self.odl_file_entry.grid(row=0, column=0, sticky='ew')
        self.odl_button.grid(row=0, column=5, pady=5, padx=(0, 5), sticky='w')
        self.code_file_label.grid(row=1, column=0, pady=(0, 5), sticky='e')
        self.code_frame.grid(row=1, column=1, padx=5,
                             pady=(0, 5), sticky='ew')
        self.code_file_entry.grid(row=0, column=0, sticky='ew')
        self.function_label.grid(row=1, column=2, pady=(0, 5), sticky='e')
        self.function_frame.grid(row=1, column=3, padx=5,
                                 pady=(0, 5), sticky='ew')
        self.function_entry.grid(row=0, column=0, sticky='ew')
        self.flags_label.grid(row=1, column=4, pady=(0, 5), sticky='ew')
        self.flags_frame.grid(row=1, column=5, padx=5,
                              pady=(0, 5), sticky='ew')
        self.flags_entry.grid(row=0, column=0, sticky='ew')
        self.search_button.grid(row=1, column=6, pady=(0, 5), sticky='w')

        # Update function options when code file changes
        self.code_file_entry.bind("<<ComboboxSelected>>", lambda e:
                                  [self.update_function_options(), self.onpress(e)])

        # Update flag options when function changes
        self.function_entry.bind("<<ComboboxSelected>>", lambda e:
                                 [self.update_flag_options(), self.onpress(e)])

        self.flags_entry.bind("<<ComboboxSelected>>", lambda e: self.onpress(e))
        
        self.odl_file_entry.bind('<Return>', lambda e: self.open_odl(ellipsis=False))

    def onpress(self, event):
        event.widget.focus_force()
        keyboard.press('right')
    
    def retrieve_values(self):
        # Get and strip values
        odl_value = self.odl.get().strip()
        cfv_value = self.cfv.get().strip()
        funcv_value = self.funcv.get().strip()
        flagsv_value = self.flagsv.get().strip()

        # Configure frames based on values
        self.odl_frame.config(bd=2 if not odl_value else 0, bg="red" if not odl_value else ttk.Style().lookup('TFrame', 'background'))
        self.code_frame.config(bd=2 if not cfv_value else 0, bg="red" if not cfv_value else ttk.Style().lookup('TFrame', 'background'))
        self.function_frame.config(bd=2 if not funcv_value else 0, bg="red" if not funcv_value else ttk.Style().lookup('TFrame', 'background'))
        self.flags_frame.config(bd=2 if not flagsv_value else 0, bg="red" if not flagsv_value else ttk.Style().lookup('TFrame', 'background'))

        # If any value is empty, return
        if not (odl_value and cfv_value and funcv_value and flagsv_value):
            return

        self.odl_file_entry.config(state='disabled')
        self.odl_button.config(state='disabled')
        self.code_file_entry.config(state='disabled')
        self.parent.retrieve_search_values(odl_value,
                                           cfv_value,
                                           funcv_value,
                                           flagsv_value)

    def open_odl(self, ellipsis=True):
        if ellipsis:
            filename = filedialog.askopenfilename(initialdir="/",
                                                  title="Open",
                                                  filetypes=(("ODL file",
                                                              "*.odl *.odlgz *.odlsent *.aodl"),))
        else:
            filename = self.odl.get().strip()

        if filename:
            self.odl.set(filename)
            self.parent.odl.process_odl(filename, '', self.parent, search=False)
    
            if self.parent.odl.code_file:
                # Populate and sort the code file list
                self.code_file_list = sorted(self.parent.odl.code_file, key=str.lower)
                self.function_dict = self.parent.odl.function
                self.flags_dict = self.parent.odl.flags

                # Set entries to read-only
                self.code_file_entry.config(state='readonly')
                self.function_entry.config(state='readonly')
                self.flags_entry.config(state='readonly')
        
                # Enable the search button
                self.search_button.config(state='active')

                # Update code file entry values
                self.code_file_entry['values'] = self.code_file_list
                self.code_file_entry.set('')  # Reset selection
            else:
                self._clear_code_file_entries()
        else:
            self._clear_code_file_entries()

    def _clear_code_file_entries(self):
        """Helper function to clear code file-related entries."""
        self.code_file_entry.config(state='disabled')
        self.function_entry.config(state='disabled')
        self.flags_entry.config(state='disabled')
        self.search_button.config(state='disabled')
        self.code_file_list.clear()
        self.cfv.set('')
        self.code_file_entry.set('')  # Reset selection

    def update_function_options(self, event=None):
        selected_code_file = self.code_file_entry.get()
        self.focus()
        if selected_code_file in self.function_dict:
            self.function_entry['values'] = sorted(self.function_dict[selected_code_file], key=str.lower)
            self.function_entry.set('')  # Reset selection
            self.flags_entry.set('')
        else:
            self.function_entry['values'] = []

    def update_flag_options(self, event=None):
        selected_function = self.function_entry.get()
        self.focus()
        if selected_function in self.flags_dict:
            self.flags_entry['values'] = sorted(self.flags_dict[selected_function])
            self.flags_entry.set('')  # Reset selection
        else:
            self.flags_entry['values'] = []

    def reset_variables(self):
        self.code_file_list = []
        self.function_dict = {}
        self.flags_dict = {}
        self.code_file_entry['values'] = []
        self.function_entry['values'] = []
        self.flags_entry['values'] = []
        self.odl.set('')
        self.cfv.set('')
        self.funcv.set('')
        self.flagsv.set('')
        self.odl_file_entry.config(state='active')
        self.odl_button.config(state='active')
        self.code_file_entry.config(state='disabled')
        self.function_entry.config(state='disabled')
        self.flags_entry.config(state='disabled')
        self.search_button.config(state='disabled')
        self.odl_frame.config(bd=0, bg=ttk.Style().lookup('TFrame', 'background'))
        self.code_frame.config(bd=0, bg=ttk.Style().lookup('TFrame', 'background'))
        self.function_frame.config(bd=0, bg=ttk.Style().lookup('TFrame', 'background'))
        self.flags_frame.config(bd=0, bg=ttk.Style().lookup('TFrame', 'background'))


class DataFrame:
    def __init__(self, master):
        self.master = master
        self.data_frame = ttk.Frame(master)
        self.data_text = tk.Text(self.data_frame,
                                 font=('Consolas', 12, 'normal'),
                                 width=65,
                                 padx=5,
                                 pady=5,
                                 state='disabled')

        self.setup_scrollbar()
        self.setup_layout()

    def setup_scrollbar(self):
        self.scrollb = ttk.Scrollbar(self.data_frame,
                                     command=self.data_text.yview)
        self.data_text.configure(yscrollcommand=self.scrollb.set)

    def setup_layout(self):
        self.data_text.grid(row=0, column=0, sticky="nsew")
        self.scrollb.grid(row=0, column=1, sticky="ns")
        self.data_frame.rowconfigure(0, weight=1)
        self.data_frame.columnconfigure(0, weight=1)

    def update_data_text(self, data):
        self.data_text.config(state='normal')
        self.data_text.delete(1.0, tk.END)  # Clear the existing content
        formatted_data = self.format_bytes(data)
        self.data_text.insert(tk.END, formatted_data)  # Insert new data
        self.data_text.config(state='disabled')

    @staticmethod
    def format_bytes(data, bytes_per_line=16):
        hex_str = ''.join(f'{byte:02X} ' for byte in data)
        ascii_str = ''.join(chr(byte) if 32 <= byte < 127 else '.' for byte in data)
        lines = []
        for i in range(0, len(data), bytes_per_line):
            hex_slice = hex_str[i*3:(i+bytes_per_line)*3].ljust(48)
            ascii_slice = ascii_str[i:i+bytes_per_line]
            lines.append(hex_slice + ' ' + ascii_slice)
        return '\n'.join(lines)


class InformationFrame:
    def __init__(self, master):
        self.master = master
        self.information_frame = ttk.Frame(master)
        self.dv = tk.StringVar()
        self.av = tk.StringVar()
        self.vv = tk.StringVar()
        self.iv = tk.StringVar()
        self.cv = tk.StringVar()

        self.description_label = ttk.Label(self.information_frame,
                                           text="Description:")
        self.author_label = ttk.Label(self.information_frame, text="Author:")
        self.version_label = ttk.Label(self.information_frame, text="Version:")
        self.id_label = ttk.Label(self.information_frame, text="Id:")
        self.code_file_label = ttk.Label(self.information_frame,
                                         text="Code_File:")

        self.description_frame = tk.Frame(self.information_frame, takefocus=False, bg=ttk.Style().lookup('TFrame', 'background'))
        self.author_frame = tk.Frame(self.information_frame, takefocus=False, bg=ttk.Style().lookup('TFrame', 'background'))
        self.version_frame = tk.Frame(self.information_frame, takefocus=False, bg=ttk.Style().lookup('TFrame', 'background'))

        self.description_entry = ttk.Entry(self.description_frame, width=40,
                                           textvariable=self.dv, state='disabled')
        self.author_entry = ttk.Entry(self.author_frame, width=40,
                                      textvariable=self.av, state='disabled')
        self.version_entry = ttk.Entry(self.version_frame, width=40,
                                       textvariable=self.vv, state='disabled')
        self.id_entry = ttk.Entry(self.information_frame, width=40,
                                  textvariable=self.iv, state='disabled')
        self.code_file_entry = ttk.Entry(self.information_frame, width=40,
                                         textvariable=self.cv, state='disabled')

        self.setup_layout()

        # Validate version_entry as float
        self.validate_float()

    def setup_layout(self):
        self.description_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.author_label.grid(row=1, column=0, padx=5, pady=(0, 5), sticky='w')
        self.version_label.grid(row=2, column=0, padx=5, pady=(0, 5), sticky='w')
        self.id_label.grid(row=3, column=0, padx=5, pady=(0, 5), sticky='w')
        self.code_file_label.grid(row=4, column=0, padx=5, pady=(0, 5), sticky='w')

        self.description_entry.grid(row=0, column=0, sticky='w')
        self.author_entry.grid(row=0, column=0, sticky='w')
        self.version_entry.grid(row=0, column=0, sticky='w')

        self.description_frame.grid(row=0, column=1, pady=5, sticky='w')
        self.author_frame.grid(row=1, column=1, pady=(0, 5), sticky='w')
        self.version_frame.grid(row=2, column=1, pady=(0, 5), sticky='w')
        self.id_entry.grid(row=3, column=1, pady=(0, 5), sticky='w')
        self.code_file_entry.grid(row=4, column=1, pady=(0, 5), sticky='w')

    def validate_float(self):
        def validate_version(action, value_if_allowed):
            if action == '1':  # insert
                try:
                    float(value_if_allowed)
                    return True
                except ValueError:
                    return False
            else:  # delete
                return True

        validate_version_cmd = self.master.register(validate_version)
        self.version_entry.configure(validate='key',
                                     validatecommand=(validate_version_cmd,
                                                      '%d', '%P'))

    def reset_variables(self):
        self.dv.set('')
        self.av.set('')
        self.vv.set('')
        self.iv.set('')
        self.cv.set('')
        self.description_entry.config(state='disabled')
        self.author_entry.config(state='disabled')
        self.version_entry.config(state='disabled')
        self.description_frame.config(bd=0, bg=ttk.Style().lookup('TFrame', 'background'))
        self.author_frame.config(bd=0, bg=ttk.Style().lookup('TFrame', 'background'))
        self.version_frame.config(bd=0, bg=ttk.Style().lookup('TFrame', 'background'))

# https://stackoverflow.com/questions/39458337/is-there-a-way-to-add-close-buttons-to-tabs-in-tkinter-ttk-notebook
class NotebookManager(ttk.Notebook):
    """A ttk Notebook with close buttons on each tab"""

    __initialized = False

    def __init__(self, parent_frame, parent, *args, **kwargs):
        super().__init__(parent_frame, **kwargs)
        self.parent_frame = parent_frame
        self.parent = parent
        if not self.__initialized:
            self.__initialize_custom_style()
            self.__inititialized = True

        self.config(style="CustomNotebook")

        self._active = None

        self.bind("<ButtonPress-1>", self.on_close_press, True)
        self.bind("<ButtonRelease-1>", self.on_close_release)

    def on_close_press(self, event):
        """Called when the button is pressed over the close button"""

        if event.widget.winfo_class() != 'TNotebook':
            return
        
        element = self.identify(event.x, event.y)

        if "close" in element:
            try:
                index = self.index("@%d,%d" % (event.x, event.y))
            except Exception:
                return
            self.state(['pressed'])
            self._active = index
            return "break"

    def on_close_release(self, event):
        """Called when the button is released"""
        if event.widget.winfo_class() != 'TNotebook':
            return
        
        if not self.instate(['pressed']):
            return

        element =  self.identify(event.x, event.y)
        if "close" not in element:
            # user moved the mouse off of the close button
            return

        index = self.index("@%d,%d" % (event.x, event.y))

        if self._active == index and len(self.tabs()) > 1:
            self.parent.remove_function(index)
            self.forget(index)
            self.event_generate("<<NotebookTabClosed>>")
            self.update_tab_names()
            self.parent.data_frame.update_data_text('')
            self.parent.output_frame.update_data_text('')
            self.parent.data_dict = self.parent.adjust_dict_keys(self.parent.data_dict, index)
            self.parent.output_dict = self.parent.adjust_dict_keys(self.parent.output_dict, index)

        self.state(["!pressed"])
        self._active = None

    def iter_layout(self, layout):
        """Recursively prints the layout children."""
        elements = ''
        for element, child in layout:
            if 'focus' in element:
                for key, value in child.items():
                    if not isinstance(value, str):
                        elements += self.iter_layout(value)
                continue
            elements += f"('{element}', {{"
            for key, value in child.items():
                if isinstance(value, str):
                    elements += f"'{key}': '{value}', "
                else:
                    elements += f"'{key}': ["
                    elements += self.iter_layout(value)
                    elements += (']')
            elements += '})'
        return elements

    def __initialize_custom_style(self):
        style = ttk.Style()
        
        TNotebook_map = style.map('TNotebook.Tab')
        style.map('CustomNotebook.Tab', **TNotebook_map)

        try:
            style.element_create("close", "image", "img_close",
                                ("active", "pressed", "!disabled", "img_closepressed"),
                                ("active", "!disabled", "img_closeactive"), border=8, sticky='')
        except Exception:
            pass
        style.layout("CustomNotebook", [("CustomNotebook.client", {"sticky": "nswe"})])
        layout = style.layout('TNotebook.Tab')
        elements = self.iter_layout(layout)
        elements = elements.replace("label', {'sticky': 'nswe', }", "label', {'side': 'left', 'sticky': '', }").replace("label', {'side': 'top'", "label', {'side': 'left'").replace(", })", "}), ('Notebook.close', {'side': 'left', 'sticky': ''})")
        elements = ast.literal_eval(elements)

        try:
            style.layout("CustomNotebook.Tab", [elements])
        except Exception:
            style.layout("CustomNotebook.Tab", list(elements))
            
        try:
            style.configure('CustomNotebook.Tab', **style.configure('TNotebook.Tab'))
            style.configure('CustomNotebook', **style.configure('TNotebook'))
        except Exception:
            pass
            
    def update_tab_names(self):
        for index in range(self.index('end')):
            tab_text = f"Func {index}  "
            self.tab(index, text=tab_text)

    def create_tab(self):
        new_tab = ttk.Frame(self, takefocus=False)
        self.add(new_tab, text=f"Func {self.index('end')}  ")
        return new_tab, self.index('end')

    def add_function_and_structure_frames(self, tab_frame,
                                          funcv_value, flagsv_value):
        function_frame = FunctionFrame(tab_frame, text="Functions:", takefocus=False, padding=5)
        function_frame.funcv.set(funcv_value)
        function_frame.flagsv.set(flagsv_value)
        function_frame.grid(row=0, column=0, sticky="nsew")
        structure_frame = StructureFrame(tab_frame, self.parent,
                                         text="Structure:", takefocus=False)
        self.parent.pane_config()
        structure_frame.grid(row=1, column=0, sticky="nsew")

    def style_change(self):
        self.__initialize_custom_style()
        self.config(style="CustomNotebook")
        self._active = None

class FunctionFrame(ttk.LabelFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master
        self.funcv = tk.StringVar()
        self.dv = tk.StringVar()
        self.flagsv = tk.StringVar()

        self.function_label = ttk.Label(self, text="Function:")
        self.description_label = ttk.Label(self, text="Description:")
        self.flags_label = ttk.Label(self, text="Flags:")

        self.description_frame = tk.Frame(self, takefocus=False, bg=ttk.Style().lookup('TFrame', 'background'))

        self.function_entry = ttk.Entry(self,
                                        width=40,
                                        textvariable=self.funcv,
                                        state='disabled')
        self.description_entry = ttk.Entry(self.description_frame,
                                           width=40,
                                           textvariable=self.dv)
        self.flags_entry = ttk.Entry(self,
                                     width=40,
                                     textvariable=self.flagsv,
                                     state='disabled')

        self.setup_layout()

    def setup_layout(self):
        self.function_label.grid(row=0, column=0, padx=(0, 5),
                                 pady=(0, 5), sticky='w')
        self.description_label.grid(row=1, column=0, padx=(0, 5),
                                    pady=(0, 5), sticky='w')
        self.flags_label.grid(row=2, column=0, padx=(0, 5),
                              pady=(0, 5), sticky='w')

        self.description_entry.grid(row=0, column=0)

        self.function_entry.grid(row=0, column=1, pady=(0, 5))
        self.description_frame.grid(row=1, column=1, pady=(0, 5))
        self.flags_entry.grid(row=2, column=1, pady=(0, 5))


class StructureFrame(ttk.LabelFrame):
    def __init__(self, master, parent, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master
        self.parent = parent
        self.rows = []
        self.structure_frame = ttk.LabelFrame(master, text="Structure:", takefocus=False)
        self.add_button = ttk.Button(self, image=self.parent.add_img, takefocus=False,
                                     command=self.create_entry)
        self.test_button = ttk.Button(self, image=self.parent.test_img, takefocus=False,
                                      command=lambda: self.run_test(self.parent.odl.params))
        self.add_button.grid(row=0, column=0, pady=(0, 5), sticky="e")  # Grid add_button at row 0, column 0, aligned to east
        self.test_button.grid(row=3, column=0, pady=5, sticky="s")  # Grid test_button at row 1, column 0, aligned to south

        # Create a canvas for scrollable area
        self.canvas = tk.Canvas(self, highlightthickness=0, height=200, takefocus=False)
        self.canvas.grid(row=1, column=0, rowspan=2, sticky="nswe")  # Grid canvas spanning rows 0 and 1, column 1, expanding in all directions

        # Add a scrollbar to the canvas
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview, takefocus=False)
        self.scrollbar.grid(row=1, column=2, rowspan=2, sticky="ns")  # Grid scrollbar spanning rows 0 and 1, column 2, aligned to north and south

        # Configure canvas to use scrollbar
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Create a frame inside the canvas to contain the rows
        self.inner_frame = ttk.Frame(self.canvas, takefocus=False)
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor=tk.NW)

        # Bind mousewheel scrolling to the canvas
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)

        # Configure scrollbar and canvas resizing
        self.inner_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"), width=e.width))

        # Set initial mousewheel binding state
        self.is_mousewheel_enabled = False

    def on_mousewheel(self, event):
        if self.is_mousewheel_enabled:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def create_entry(self):
        new_row = ttk.Frame(self.inner_frame, takefocus=False)
        new_row.grid(sticky="ew")  # Grid new_row, expanding horizontally
        options_list = ('int8', 'int8', 'uint8', 'int16', 'uint16', 'int32',
                        'uint32', 'int64', 'uint64', 'float16', 'float',
                        'double', 'char', 'wchar', 'int24', 'uint24', 'int48',
                        'uint48', 'int128', 'uint128', 'uleb128', 'ileb128',
                        'void')
        v = tk.StringVar()
        v.set(options_list[0])
        om = ttk.OptionMenu(new_row, v, *options_list)
        om.bind("<FocusIn>", self.focus_next_widget)
        om.grid(row=0, column=0, sticky="e")  # Grid om at row 0, column 0

        entry = ttk.Entry(new_row, width=40)
        entry.grid(row=0, column=1, sticky="e")  # Grid entry at row 0, column 1

        remove_button = ttk.Button(new_row, image=self.parent.minus_img, takefocus=False,
                                   command=lambda: self.remove_row(new_row))
        remove_button.grid(row=0, column=2, sticky="e")  # Grid remove_button at row 0, column 2

        self.rows.append((new_row, v, entry))

        # Adjust canvas scrolling region
        self.canvas.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

        # Check if canvas content exceeds its visible area
        if self.canvas.winfo_height() < self.inner_frame.winfo_reqheight():
            self.enable_mousewheel()
        else:
            self.disable_mousewheel()

        new_row.grid_columnconfigure(1, weight=1)

    def remove_row(self, row):
        row.destroy()
        self.rows = [r for r in self.rows if r[0] != row]

        # Adjust canvas scrolling region
        self.canvas.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

        # Check if canvas content exceeds its visible area
        if self.canvas.winfo_height() < self.inner_frame.winfo_reqheight():
            self.enable_mousewheel()
        else:
            self.disable_mousewheel()

    def enable_mousewheel(self):
        if not self.is_mousewheel_enabled:
            self.master.bind_all("<MouseWheel>", self.on_mousewheel)
            self.is_mousewheel_enabled = True

    def disable_mousewheel(self):
        if self.is_mousewheel_enabled:
            self.master.unbind_all("<MouseWheel>")
            self.is_mousewheel_enabled = False

    def focus_next_widget(self, event):
        event.widget.tk_focusNext().focus()
        return "break"

    def run_test(self, data):
        template = "struct test {\n"
        for row in self.rows:
            om_value = row[1].get()
            entry_value = row[2].get()
            template += f"\t{om_value} {entry_value};\n"
        template += "};"
        self.cparser = cstruct.cstruct()
        try:
            self.cparser.load(template)
            params = self.cparser.test(data)
            test = cstruct.dumpstruct(params, output='string')
        except Exception as e:
            test = str(e)

        self.parent.output_frame.update_data_text(test)
        self.parent.output_dict[self.parent.notebook_manager.index(self.parent.notebook_manager.select())] = test


class DocumentFrame:
    def __init__(self, master):
        self.master = master
        self.doc_frame = ttk.LabelFrame(master, text="# Documentation", takefocus=False)
        self.doc_text = tk.Text(self.doc_frame, height=5, padx=5, pady=5)
        self.doc_text.insert("1.0", "N/A")

        self.setup_scrollbar()
        self.setup_layout()

    def setup_scrollbar(self):
        self.scrollb = ttk.Scrollbar(self.doc_frame,
                                     command=self.doc_text.yview)
        self.doc_text.configure(yscrollcommand=self.scrollb.set)

    def setup_layout(self):
        self.doc_text.grid(row=0, column=0, sticky="nsew")
        self.scrollb.grid(row=0, column=1, sticky="ns")
        self.doc_frame.rowconfigure(0, weight=1)
        self.doc_frame.columnconfigure(0, weight=1)


class OutputFrame:
    def __init__(self, master):
        self.master = master
        self.output_frame = ttk.Frame(master)

        self.output_text = tk.Text(self.output_frame,
                                   undo=False,
                                   bg='black',
                                   fg='light grey',
                                   font=('Consolas', 12, 'normal'),
                                   width=77,
                                   padx=5,
                                   pady=5,
                                   state='disabled')

        self.setup_tags()
        self.setup_scrollbar()
        self.setup_layout()

    def setup_tags(self):
        tags = {
            b'\x1b[1;31m': {"foreground": "red"},
            b'\x1b[1;32m': {"foreground": "green"},
            b'\x1b[1;92m': {"foreground": "green", "font": ('Consolas', 12, 'bold')},
            b'\x1b[1;33m': {"foreground": "yellow"},
            b'\x1b[1;93m': {"foreground": "yellow", "font": ('Consolas', 12, 'bold')},
            b'\x1b[1;34m': {"foreground": '#3B78FF'},
            b'\x1b[1;35m': {"foreground": "purple"},
            b'\x1b[1;36m': {"foreground": "cyan"},
            b'\x1b[1;37m': {"foreground": "white"},
            b'\x1b[1;41m\x1b[1;37m': {"background": '#C50F1F'},
            b'\x1b[1;42m\x1b[1;37m': {"background": '#13A10E'},
            b'\x1b[1;43m\x1b[1;37m': {"background": '#C19C00'},
            b'\x1b[1;44m\x1b[1;37m': {"background": '#0037DA'},
            b'\x1b[1;45m\x1b[1;37m': {"background": '#881798'},
            b'\x1b[1;46m\x1b[1;37m': {"background": '#3A96DD'},
            b'\x1b[1;47m\x1b[1;30m': {"background": '#CCCCCC', "foreground": '#767693'},
            b'\x1b[1;0m\x1b[1;41m\x1b[1;37m': {"background": '#C50F1F'},
            b'\x1b[1;0m\x1b[1;42m\x1b[1;37m': {"background": '#13A10E'},
            b'\x1b[1;0m\x1b[1;43m\x1b[1;37m': {"background": '#C19C00'},
            b'\x1b[1;0m\x1b[1;44m\x1b[1;37m': {"background": '#0037DA'},
            b'\x1b[1;0m\x1b[1;45m\x1b[1;37m': {"background": '#881798'},
            b'\x1b[1;0m\x1b[1;46m\x1b[1;37m': {"background": '#3A96DD'},
            b'\x1b[1;0m\x1b[1;47m\x1b[1;30m': {"background": '#CCCCCC', "foreground": '#767693'}
        }

        for tag, options in tags.items():
            self.output_text.tag_configure(tag, **options)

    def setup_scrollbar(self):
        self.scrollb = ttk.Scrollbar(self.output_frame,
                                     command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=self.scrollb.set)

    def setup_layout(self):
        self.output_text.grid(row=0, column=0, sticky="nsew")
        self.scrollb.grid(row=0, column=1, sticky="ns")
        self.output_frame.rowconfigure(0, weight=1)
        self.output_frame.columnconfigure(0, weight=1)

    def update_data_text(self, data):
        self.output_text.config(state='normal')
        self.output_text.delete(1.0, tk.END)
        ansi_escape = re.compile('((?:\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])){3}|(?:\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])){2}|(?:\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])))')
        line = ansi_escape.split(data)
        s = len(line)

        if s % 2 != 0:
            s = s - 1

        self.output_text.insert(tk.END, line[0].lstrip())

        for i in range(1, s, 2):
            tag = line[i]
            w = line[i+1]

            self.output_text.insert(tk.END, w, tag)

        self.output_text.config(state='disabled')


class ODL:
    def __init__(self):
        self.headers = '''
        typedef struct _Odl_header{
            char    signature[8];  // EBFGONED
            uint32    odl_version;
            uint32    unk1;
            uint64    unk2;
            uint32    unk3;
            char      one_drive_version[0x40];
            char      windows_version[0x40];
            char      reserved[0x64];
        } Odl_header;

        typedef struct _Data_block_V2{
            uint64     signature;  // CCDDEEFF00000000
            uint64     timestamp;
            uint32     unk1;
            uint32     unk2;
            uint128    unk3_guid;
            uint32     unk4;
            uint32     unk5;
            uint32     data_len;
            uint32     unk6;
            // followed by Data
        } Data_block_V2;

        typedef struct _Data_block_V3{
            uint64    signature;  // CCDDEEFF00000000
            uint64    timestamp;
            uint32    unk1;
            uint32    unk2;
            uint32    data_len;
            uint32    unk3;
            // followed by Data
        } Data_block_V3;

        typedef struct _Data_v2{
            uint32    code_file_name_len;
            char      code_file_name[code_file_name_len];
            uint32    flags;
            uint32    code_function_name_len;
            char      code_function_name[code_function_name_len];
        } Data_v2;

        typedef struct _Data_v3{
            uint128    unk1_guid;
            uint32     unk2;
            uint32     unk3;
            uint32     code_file_name_len;
            char       code_file_name[code_file_name_len];
            uint32     flags;
            uint32     code_function_name_len;
            char       code_function_name[code_function_name_len];
        } Data_v3;

        '''
        self.cparser = cstruct.cstruct()
        self.cparser.load(self.headers)
        self.code_file = []
        self.function = {}
        self.flags = {}
        self.params = ''

    def process_odl(self, filename, func_find, parent, search=True):
        parent.output_frame.update_data_text('')
        basename = os.path.basename(filename)
        if not search:
            self.code_file.clear()
            self.function.clear()
            self.flags.clear()
        self.params = ''
        try:
            f = open(filename, 'rb')
        except Exception as e:
            parent.output_frame.update_data_text(f'{e}')
            return
        with f:
            try:
                header = self.cparser.Odl_header(f.read(0x100))
            except Exception as e:
                parent.output_frame.update_data_text(f'Unable to parse {basename}. Not a valid log file.')
                return
            if header.signature == b'EBFGONED':  # Odl header
                pass
            else:
                parent.output_frame.update_data_text(f'Bad header signature')
                return
            signature = f.read(8)
            if signature[0:4] == b'\x1F\x8B\x08\x00':  # gzip
                try:
                    f.seek(-8, 1)
                    all_data = f.read()
                    z = zlib.decompressobj(31)
                    file_data = z.decompress(all_data)
                except (zlib.error, OSError) as e:
                    parent.output_frame.update_data_text(f'..decompression error for file {basename}. {e}')
                    return
                f.close()
                f = io.BytesIO(file_data)
                signature = f.read(8)
            if signature != b'\xCC\xDD\xEE\xFF\0\0\0\0':  # CDEF header
                parent.output_frame.update_data_text(f'{basename} wrong header! Did not find 0xCCDDEEFF')
                return
            else:
                f.seek(-8, 1)
                db_size = 32 if header.odl_version == 3 else 56
                data_block = f.read(db_size)  # odl complete header is 56 bytes
            while data_block:
                if header.odl_version == 2:
                    data_block = self.cparser.Data_block_V2(data_block)
                elif header.odl_version == 3:
                    data_block = self.cparser.Data_block_V3(data_block)
                else:
                    parent.output_frame.update_data_text(f'Unknown odl_version = {header.odl_version}')
                    return
                if data_block.signature != 0xffeeddcc:
                    parent.output_frame.update_data_text(f'Unable to parse {basename} completely. Did not find 0xCCDDEEFF')
                    break
                try:
                    if header.odl_version == 3:
                        data = self.cparser.Data_v3(f.read(data_block.data_len))
                        params_len = (data_block.data_len - data.code_file_name_len - data.code_function_name_len - 36)
                    else:
                        data = self.cparser.Data_v2(f.read(data_block.data_len))
                        params_len = (data_block.data_len - data.code_file_name_len - data.code_function_name_len - 12)
                    f.seek(- params_len, io.SEEK_CUR)
                except Exception as e:
                    parent.output_frame.update_data_text(f'Unable to parse {basename} completely. {type(e).__name__}')
                    return

                if not search and params_len:
                    self.code_file.append(data.code_file_name.decode('utf8')) if data.code_file_name.decode('utf8') not in self.code_file else None
                    self.function.setdefault(data.code_file_name.decode('utf8'), []).append(data.code_function_name.decode('utf8')) if data.code_function_name.decode('utf8') not in self.function.get(data.code_file_name.decode('utf8'), []) else None
                    self.flags.setdefault(data.code_function_name.decode('utf8'), []).append(data.flags) if data.flags not in self.flags.get(data.code_function_name.decode('utf8'), []) else None

                if params_len:
                    if func_find == f"{data.code_file_name.decode('utf8').lower()}{data.code_function_name.decode('utf8').lower()}{data.flags}":
                        self.params = f.read(params_len)
                    else:
                        f.read(params_len)

                data_block = f.read(db_size)


class LabelSeparator(tk.Frame):
    def __init__(self, parent, text="", width="", *args):
        tk.Frame.__init__(self, parent, *args)

        self.bgf = ttk.Style().lookup('Label', 'background')

        self.configure(background=self.bgf)
        self.grid_columnconfigure(0, weight=1)

        self.separator = ttk.Separator(self, orient=tk.HORIZONTAL)
        self.separator.grid(row=0, column=0, padx=(10, 30), sticky="ew")

        self.label = ttk.Label(self, text=text)
        bold_font = font.Font(font=self.label['font'])
        bold_font.config(weight='bold')
        self.label.config(font=bold_font)
        self.label.grid(row=0, column=0, padx=width, sticky="w")

    def update_theme(self):
        new_bgf = ttk.Style().lookup('Label', 'background')
        self.configure(background=new_bgf)


class ParentClass:
    def __init__(self):
        self.application_path = application_path
        self.root = ThemedTk(gif_override=True)
        # self.on_move()
        # self.root.bind('<Configure>', self.on_move)
        ttk.Style().theme_use(theme_data['theme'])
        self.root.title(f'Lyman v{__version__}')
        self.root.iconbitmap(self.application_path + '/lyman/lyman.ico')
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", lambda: QuitDialog(self.root))
        self.data_dict = {}
        self.function_list = []
        self.output_dict = {}
        self.odl = ODL()
        self.add_images()
        self.setup_menu()
        self.setup_frames()
        self.pane_config()

    def get_monitor_from_position(self, x, y):
        # Get the resolution of the primary monitor
        monitors = get_monitors()
        for monitor in monitors:
            if monitor.x <= x < monitor.x + monitor.width and monitor.y <= y < monitor.y + monitor.height:
                return monitor
        return None
    
    def on_move(self):
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        monitor = self.get_monitor_from_position(x, y)
        if monitor:
            # print(f"Window is on monitor: {monitor.name}, Resolution: {monitor.width}x{monitor.height} Scale: {monitor.width/1434}")
            self.root.tk.call('tk', 'scaling', (monitor.width/1434))
        else:
            # print("Window is not on any known monitor")
            pass

    def add_images(self):
        self.images = (
        tk.PhotoImage("img_close", data='''
            R0lGODlhCwALAPcAAAAAAAAAMwAAZgAAmQAAzAAA/wArAAArMwArZgArmQArzAAr
            /wBVAABVMwBVZgBVmQBVzABV/wCAAACAMwCAZgCAmQCAzACA/wCqAACqMwCqZgCq
            mQCqzACq/wDVAADVMwDVZgDVmQDVzADV/wD/AAD/MwD/ZgD/mQD/zAD//zMAADMA
            MzMAZjMAmTMAzDMA/zMrADMrMzMrZjMrmTMrzDMr/zNVADNVMzNVZjNVmTNVzDNV
            /zOAADOAMzOAZjOAmTOAzDOA/zOqADOqMzOqZjOqmTOqzDOq/zPVADPVMzPVZjPV
            mTPVzDPV/zP/ADP/MzP/ZjP/mTP/zDP//2YAAGYAM2YAZmYAmWYAzGYA/2YrAGYr
            M2YrZmYrmWYrzGYr/2ZVAGZVM2ZVZmZVmWZVzGZV/2aAAGaAM2aAZmaAmWaAzGaA
            /2aqAGaqM2aqZmaqmWaqzGaq/2bVAGbVM2bVZmbVmWbVzGbV/2b/AGb/M2b/Zmb/
            mWb/zGb//5kAAJkAM5kAZpkAmZkAzJkA/5krAJkrM5krZpkrmZkrzJkr/5lVAJlV
            M5lVZplVmZlVzJlV/5mAAJmAM5mAZpmAmZmAzJmA/5mqAJmqM5mqZpmqmZmqzJmq
            /5nVAJnVM5nVZpnVmZnVzJnV/5n/AJn/M5n/Zpn/mZn/zJn//8wAAMwAM8wAZswA
            mcwAzMwA/8wrAMwrM8wrZswrmcwrzMwr/8xVAMxVM8xVZsxVmcxVzMxV/8yAAMyA
            M8yAZsyAmcyAzMyA/8yqAMyqM8yqZsyqmcyqzMyq/8zVAMzVM8zVZszVmczVzMzV
            /8z/AMz/M8z/Zsz/mcz/zMz///8AAP8AM/8AZv8Amf8AzP8A//8rAP8rM/8rZv8r
            mf8rzP8r//9VAP9VM/9VZv9Vmf9VzP9V//+AAP+AM/+AZv+Amf+AzP+A//+qAP+q
            M/+qZv+qmf+qzP+q///VAP/VM//VZv/Vmf/VzP/V////AP//M///Zv//mf//zP//
            /wAAAAAAAAAAAAAAACH5BAEAAPwALAAAAAALAAsAAAhTAIlN6jVwYCNJtyZNEkiw
            YK9GjHxN2rfPIMVJjAZS3Ndooy2FBDdSlASRYEiKjG6RbHRyI6NeGXttlInyJSOK
            DyXhZBQzIy+VtngS44nxoNFJAQEAOw
            '''),
        tk.PhotoImage("img_closeactive", data='''
            R0lGODlhCwALAPcAAAAAAAAAMwAAZgAAmQAAzAAA/wArAAArMwArZgArmQArzAAr
            /wBVAABVMwBVZgBVmQBVzABV/wCAAACAMwCAZgCAmQCAzACA/wCqAACqMwCqZgCq
            mQCqzACq/wDVAADVMwDVZgDVmQDVzADV/wD/AAD/MwD/ZgD/mQD/zAD//zMAADMA
            MzMAZjMAmTMAzDMA/zMrADMrMzMrZjMrmTMrzDMr/zNVADNVMzNVZjNVmTNVzDNV
            /zOAADOAMzOAZjOAmTOAzDOA/zOqADOqMzOqZjOqmTOqzDOq/zPVADPVMzPVZjPV
            mTPVzDPV/zP/ADP/MzP/ZjP/mTP/zDP//2YAAGYAM2YAZmYAmWYAzGYA/2YrAGYr
            M2YrZmYrmWYrzGYr/2ZVAGZVM2ZVZmZVmWZVzGZV/2aAAGaAM2aAZmaAmWaAzGaA
            /2aqAGaqM2aqZmaqmWaqzGaq/2bVAGbVM2bVZmbVmWbVzGbV/2b/AGb/M2b/Zmb/
            mWb/zGb//5kAAJkAM5kAZpkAmZkAzJkA/5krAJkrM5krZpkrmZkrzJkr/5lVAJlV
            M5lVZplVmZlVzJlV/5mAAJmAM5mAZpmAmZmAzJmA/5mqAJmqM5mqZpmqmZmqzJmq
            /5nVAJnVM5nVZpnVmZnVzJnV/5n/AJn/M5n/Zpn/mZn/zJn//8wAAMwAM8wAZswA
            mcwAzMwA/8wrAMwrM8wrZswrmcwrzMwr/8xVAMxVM8xVZsxVmcxVzMxV/8yAAMyA
            M8yAZsyAmcyAzMyA/8yqAMyqM8yqZsyqmcyqzMyq/8zVAMzVM8zVZszVmczVzMzV
            /8z/AMz/M8z/Zsz/mcz/zMz///8AAP8AM/8AZv8Amf8AzP8A//8rAP8rM/8rZv8r
            mf8rzP8r//9VAP9VM/9VZv9Vmf9VzP9V//+AAP+AM/+AZv+Amf+AzP+A//+qAP+q
            M/+qZv+qmf+qzP+q///VAP/VM//VZv/Vmf/VzP/V////AP//M///Zv//mf//zP//
            /wAAAAAAAAAAAAAAACH5BAEAAPwALAAAAAALAAsAAAhUAN21Y3fOnEFz4L61W7jw
            HEGD4Got3LcPIsWE5tpRrLjxmy1zBTdeNPfNYEiKB2uBMyhyHzuEKzeak/ntGziU
            DlHWLLnyoLlytc7VqvVtaNGi5gICADs
            '''),
        tk.PhotoImage("img_closepressed", data='''
            R0lGODlhCwALAPcAAAAAAAAAMwAAZgAAmQAAzAAA/wArAAArMwArZgArmQArzAAr
            /wBVAABVMwBVZgBVmQBVzABV/wCAAACAMwCAZgCAmQCAzACA/wCqAACqMwCqZgCq
            mQCqzACq/wDVAADVMwDVZgDVmQDVzADV/wD/AAD/MwD/ZgD/mQD/zAD//zMAADMA
            MzMAZjMAmTMAzDMA/zMrADMrMzMrZjMrmTMrzDMr/zNVADNVMzNVZjNVmTNVzDNV
            /zOAADOAMzOAZjOAmTOAzDOA/zOqADOqMzOqZjOqmTOqzDOq/zPVADPVMzPVZjPV
            mTPVzDPV/zP/ADP/MzP/ZjP/mTP/zDP//2YAAGYAM2YAZmYAmWYAzGYA/2YrAGYr
            M2YrZmYrmWYrzGYr/2ZVAGZVM2ZVZmZVmWZVzGZV/2aAAGaAM2aAZmaAmWaAzGaA
            /2aqAGaqM2aqZmaqmWaqzGaq/2bVAGbVM2bVZmbVmWbVzGbV/2b/AGb/M2b/Zmb/
            mWb/zGb//5kAAJkAM5kAZpkAmZkAzJkA/5krAJkrM5krZpkrmZkrzJkr/5lVAJlV
            M5lVZplVmZlVzJlV/5mAAJmAM5mAZpmAmZmAzJmA/5mqAJmqM5mqZpmqmZmqzJmq
            /5nVAJnVM5nVZpnVmZnVzJnV/5n/AJn/M5n/Zpn/mZn/zJn//8wAAMwAM8wAZswA
            mcwAzMwA/8wrAMwrM8wrZswrmcwrzMwr/8xVAMxVM8xVZsxVmcxVzMxV/8yAAMyA
            M8yAZsyAmcyAzMyA/8yqAMyqM8yqZsyqmcyqzMyq/8zVAMzVM8zVZszVmczVzMzV
            /8z/AMz/M8z/Zsz/mcz/zMz///8AAP8AM/8AZv8Amf8AzP8A//8rAP8rM/8rZv8r
            mf8rzP8r//9VAP9VM/9VZv9Vmf9VzP9V//+AAP+AM/+AZv+Amf+AzP+A//+qAP+q
            M/+qZv+qmf+qzP+q///VAP/VM//VZv/Vmf/VzP/V////AP//M///Zv//mf//zP//
            /wAAAAAAAAAAAAAAACH5BAEAAPwALAAAAAALAAsAAAhqACVR0aKlEKGDBnkVJPSK
            0KJXtCC+0kJoWLtCrlwNG7bIFaFC7YS1q9jOHESDGs8NYzfslaKGhWgVYnnOVa2I
            DAm1G3ZO2LBaEAnVGmZumMZ2vGrVMshSIstaHoHajAj1Jq+GtYTGBMorIAA7
            '''),
        )
        
        self.add_img = ImageTk.PhotoImage(Image.open(application_path + '/Lyman/plus_green.png'))
        self.minus_img = ImageTk.PhotoImage(Image.open(application_path + '/Lyman/minus_red.png'))
        self.test_img = ImageTk.PhotoImage(Image.open(application_path + '/Lyman/yes.png'))
        self.save_img = ImageTk.PhotoImage(Image.open(application_path + '/Lyman/floppy_35inch_green.png'))
        self.undo_img = ImageTk.PhotoImage(Image.open(application_path + '/Lyman/undo_yellow.png'))
        self.exit_img = ImageTk.PhotoImage(Image.open(application_path + '/Lyman/no.png'))
        self.skin_img = ImageTk.PhotoImage(Image.open(application_path + '/Lyman/skin.png'))
        self.search_img = ImageTk.PhotoImage(Image.open(application_path + '/Lyman/magnifier.png'))
        self.lyman_img = ImageTk.PhotoImage(Image.open(application_path + '/Lyman/lyman.png'))
        self.question_small_img = ImageTk.PhotoImage(Image.open(application_path + '/Lyman/question_small.png'))
        self.help_img = ImageTk.PhotoImage(Image.open(application_path + '/Lyman/help.png'))
        self.lyman_small_img = ImageTk.PhotoImage(Image.open(application_path + '/Lyman/lyman_small.png'))

    def setup_menu(self):
        html_file = self.application_path + '/lyman/manual/manual.html'
        file_path = os.path.abspath(html_file)
        file_url = 'file://' + file_path
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        options_menu = tk.Menu(menubar, tearoff=0)
        submenu = tk.Menu(options_menu, tearoff=0)
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        menubar.add_cascade(label="Options", menu=options_menu)
        menubar.add_cascade(label="Help", menu=help_menu)

        for theme_name in sorted(self.root.get_themes()):
            if theme_name != "breeze":  # breeze causes issues
                submenu.add_command(label=theme_name,
                                    command=lambda t=theme_name: [submenu.entryconfig(submenu.index(ttk.Style().theme_use()), background=''),
                                                                  self.root.set_theme(t),
                                                                  submenu.entryconfig(submenu.index(ttk.Style().theme_use()), background='grey'), self.pane_config()])

        options_menu.add_cascade(label="Skins", image=self.skin_img, compound='left', menu=submenu)
        file_menu.add_command(label="Export cstruct", image=self.save_img, compound='left', command=self.export_cstruct)
        file_menu.add_command(label="Clear", image=self.undo_img, compound='left',command=self.reset_variables)
        file_menu.add_command(label="Exit", image=self.exit_img, compound='left', command=lambda: QuitDialog(self.root))
        help_menu.add_command(label="Quick help", image=self.question_small_img, compound='left', command=lambda: Help(self.root))
        help_menu.add_command(label="User Manual", image=self.help_img, compound='left', command=lambda: webbrowser.open(file_url))
        help_menu.add_command(label="About", image=self.lyman_small_img, compound='left', command=lambda: About(self.root, self))
        submenu.entryconfig(submenu.index(ttk.Style().theme_use()), background='grey')

    def setup_frames(self):
        self.outer_frame = ttk.Frame(self.root)
        self.main_frame = ttk.Frame(self.outer_frame, relief='groove', padding=5)

        self.outer_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.search_frame = SearchFrame(self.main_frame, self)
        self.data_frame = DataFrame(self.main_frame)
        self.info_frame = InformationFrame(self.main_frame)
        self.notebook_manager = NotebookManager(self.main_frame, self, takefocus=False)
        self.notebook_manager.bind("<<NotebookTabChanged>>", self.on_tab_change)
        self.output_frame = OutputFrame(self.main_frame)
        self.doc_frame = DocumentFrame(self.main_frame)

        self.arrange_frames()

    def arrange_frames(self):
        self.search_frame.grid(row=0, column=0, columnspan=3, sticky="nsew")
        self.data_frame.data_frame.grid(row=1, column=1, rowspan=3, padx=(5, 0), pady=(5, 0), sticky="nsew")
        self.info_frame.information_frame.grid(row=1, column=0, pady=(5, 0), sticky="nsew")
        self.output_frame.output_frame.grid(row=1, column=2, rowspan=4, padx=5, pady=5, sticky="nsew")
        self.doc_frame.doc_frame.grid(row=4, column=0, columnspan=2, pady=5, sticky="nsew")

        self.bind_events()

    def bind_events(self):
        self.search_frame.search_button.bind("<Button-1>")

    def create_tab(self, funcv_value, flagsv_value):
        # Create a new tab
        new_tab, tab_index = self.notebook_manager.create_tab()
        if len(self.notebook_manager.tabs()) - 1 == 0:
            self.notebook_manager.grid(row=2, column=0, rowspan=2, sticky="nsew")
        self.notebook_manager.add_function_and_structure_frames(new_tab, funcv_value, flagsv_value)
        self.notebook_manager.select(tab_index - 1)
        return tab_index - 1

    def retrieve_search_values(self, odl_value, cfv_value, funcv_value, flagsv_value):
        self.info_frame.description_entry.config(stat='normal')
        self.info_frame.author_entry.config(stat='normal')
        self.info_frame.version_entry.config(stat='normal')
        if (f'{funcv_value}{flagsv_value}') not in self.function_list:
            self.function_list.append(f'{funcv_value}{flagsv_value}')
            func_find = f"{cfv_value.lower()}{funcv_value.lower()}{flagsv_value}"
            self.odl.process_odl(odl_value, func_find, self)
            if self.odl.params:
                tab_index = self.create_tab(funcv_value, flagsv_value)
                self.data_dict.setdefault(tab_index, self.odl.params)
                self.data_frame.update_data_text(self.odl.params)
                self.info_frame.iv.set(uuid.uuid4())
                self.info_frame.cv.set(cfv_value)

    def on_tab_change(self, event):
        try:
            selected_tab_index = event.widget.index("current")
        except Exception:
            return
        try:
            self.data_frame.update_data_text(self.data_dict[selected_tab_index])
        except KeyError:
            self.data_frame.update_data_text('')
        try:
            self.output_frame.update_data_text(self.output_dict[selected_tab_index])
        except KeyError:
            self.output_frame.update_data_text('')
        try:
            self.odl.params = self.data_dict[selected_tab_index]
        except KeyError:
            self.odl.params = ''

    def adjust_dict_keys(self, my_dict, key_to_remove):
        if key_to_remove in my_dict:
            del my_dict[key_to_remove]

        # Create a new dictionary with adjusted keys
        new_dict = {}
        for new_key, old_key in enumerate(sorted(my_dict.keys())):
            new_dict[new_key] = my_dict[old_key]

        return new_dict

    def remove_function(self, index):
        tab_name = self.notebook_manager.tabs()[index]
        tab = self.notebook_manager.nametowidget(tab_name)
        
        for child in tab.winfo_children():
                if isinstance(child, FunctionFrame):
                    self.function_list.remove(f'{child.funcv.get()}{child.flagsv.get()}')

    def pane_config(self):
        bg = ttk.Style().lookup('TFrame', 'background')
        bgf = ttk.Style().lookup('Treeview', 'background')
        fgf = ttk.Style().lookup('Treeview', 'foreground')

        if not fgf:
            fgf = 'black'

        self.data_frame.data_text.config(background=bgf, foreground=fgf)
        self.doc_frame.doc_text.config(background=bgf, foreground=fgf, insertbackground=fgf)
        
        try:
            self.notebook_manager.style_change()
        except Exception:
            pass
        for index in range(self.notebook_manager.index('end')):
            tab_name = self.notebook_manager.tabs()[index]
            tab = self.notebook_manager.nametowidget(tab_name)
            for child in tab.winfo_children():
                if isinstance(child, FunctionFrame):
                    child.description_frame.config(bg=bg) if child.description_frame.cget("bg") != "red" else None
                if isinstance(child, StructureFrame):
                    child.canvas.config(background=bg)

        self.search_frame.odl_frame.config(bg=bg) if self.search_frame.odl_frame.cget("bg") != "red" else None
        self.search_frame.code_frame.config(bg=bg) if self.search_frame.code_frame.cget("bg") != "red" else None
        self.search_frame.function_frame.config(bg=bg) if self.search_frame.function_frame.cget("bg") != "red" else None
        self.search_frame.flags_frame.config(bg=bg) if self.search_frame.flags_frame.cget("bg") != "red" else None
        self.info_frame.description_frame.config(bg=bg) if self.info_frame.description_frame.cget("bg") != "red" else None
        self.info_frame.author_frame.config(bg=bg) if self.info_frame.author_frame.cget("bg") != "red" else None
        self.info_frame.version_frame.config(bg=bg) if self.info_frame.version_frame.cget("bg") != "red" else None

        theme_data['theme'] = ttk.Style().theme_use()
        with open("lyman.settings", "w") as jsonfile:
            json.dump(theme_data, jsonfile)

    def export_cstruct(self):
        self.info_frame.description_frame.config(bd=2 if not self.info_frame.dv.get() else 0, bg="red" if not self.info_frame.dv.get() else ttk.Style().lookup('TFrame', 'background'))
        self.info_frame.author_frame.config(bd=2 if not self.info_frame.av.get() else 0, bg="red" if not self.info_frame.av.get() else ttk.Style().lookup('TFrame', 'background'))
        self.info_frame.version_frame.config(bd=2 if not self.info_frame.vv.get() else 0, bg="red" if not self.info_frame.vv.get() else ttk.Style().lookup('TFrame', 'background'))

        # If any value is empty, return
        if not (self.info_frame.dv.get() and self.info_frame.av.get() and self.info_frame.vv.get()):
            return
        template = (
            f'Description: {self.info_frame.dv.get()}\n'
            f'Author: {self.info_frame.av.get()}\n'
            f'Version: {self.info_frame.vv.get()}\n'
            f'Id: {self.info_frame.iv.get()}\n'
            f'Code_File: {self.info_frame.cv.get()}\n\n'
            f'Functions:\n'
        )

        for index in range(self.notebook_manager.index('end')):
            # Get the name of the tab at the given index
            tab_name = self.notebook_manager.tabs()[index]

            # Get the actual frame widget associated with the tab name
            tab = self.notebook_manager.nametowidget(tab_name)

            # Iterate over the children of the tab to find FunctionFrame
            for child in tab.winfo_children():
                if isinstance(child, FunctionFrame):
                    child.description_frame.config(bd=2 if not child.dv.get() else 0, bg="red" if not child.dv.get() else ttk.Style().lookup('TFrame', 'background'))
                    if not child.dv.get():
                        self.notebook_manager.select(index)
                        return
                    template += (
                        f'    -\n'
                        f'        Function: {child.funcv.get()}\n'
                        f'        Description: {child.dv.get()}\n'
                        f'        Flags: [{child.flagsv.get()}]\n'
                        f'        Structure: |\n'
                        f'            #define %s_des "%s"\n'
                        f'            struct %s {{\n'
                    )

                if isinstance(child, StructureFrame):
                    for row in child.rows:
                        template += (f'                {row[1].get()} {row[2].get()};\n')

                    template += ('            };\n')

        doc_notes = (self.doc_frame.doc_text.get("1.0", "end-1c")).replace("\n", "\n# ")

        template += (f'\n# Documentation\n# {doc_notes}\n')

        with open(f'{self.info_frame.cv.get()}.cstruct', 'w') as f:
            f.write(template)

    def reset_variables(self):
        # parent reset
        self.data_dict = {}
        self.function_list = []
        self.output_dict = {}

        # notebook reset
        self.notebook_manager.destroy()
        del self.notebook_manager
        self.notebook_manager = NotebookManager(self.main_frame, self, takefocus=False)
        self.notebook_manager.bind("<<NotebookTabChanged>>", self.on_tab_change)

        # data reset
        self.data_frame.update_data_text('')

        # search reset
        self.search_frame.code_file_entry.config(state="readonly")
        self.search_frame.reset_variables()

        # information reset
        self.info_frame.reset_variables()

        # output reset
        self.output_frame.update_data_text('')

        # document reset
        self.doc_frame.doc_text.delete(1.0, tk.END)
        self.doc_frame.doc_text.insert("1.0", "N/A")

    def run(self):
        self.root.mainloop()

if getattr(sys, 'frozen', False):
    pyi_splash.close()

parent_instance = ParentClass()
parent_instance.run()
