import os
import webbrowser
import customtkinter as ctk
from typing import Callable, Tuple
import cv2
from PIL import Image, ImageOps

import modules.globals
import modules.metadata
from modules.face_analyser import get_one_face
from modules.capturer import get_video_frame, get_video_frame_total
from modules.processors.frame.core import get_frame_processors_modules
from modules.utilities import is_image, is_video, resolve_relative_path, has_image_extension
from modules.lang.manager import LanguageManager

ROOT = None
ROOT_HEIGHT = 700
ROOT_WIDTH = 600

PREVIEW = None
PREVIEW_MAX_HEIGHT = 700
PREVIEW_MAX_WIDTH  = 1200
PREVIEW_DEFAULT_WIDTH  = 960
PREVIEW_DEFAULT_HEIGHT = 540

RECENT_DIRECTORY_SOURCE = None
RECENT_DIRECTORY_TARGET = None
RECENT_DIRECTORY_OUTPUT = None

preview_label = None
preview_slider = None
source_label = None
target_label = None
status_label = None
donate_label = None
start_button = None
stop_button = None
preview_button = None
live_button = None

use_folder_as_source_switch=None
use_folder_as_target_switch=None
keep_fps_checkbox=None
keep_frames_switch=None
enhancer_switch=None
keep_audio_switch=None
many_faces_switch=None
color_correction_switch=None

img_ft, vid_ft = modules.globals.file_types

language_manager = LanguageManager()  # Initialize the language manager
Lang=language_manager.get_language()



def init(start: Callable[[], None], destroy: Callable[[], None]) -> ctk.CTk:
    global ROOT, PREVIEW

    ROOT = create_root(start, destroy)
    PREVIEW = create_preview(ROOT)

    return ROOT

def create_root(start: Callable[[], None], destroy: Callable[[], None]) -> ctk.CTk:
    
    global source_label, target_label, status_label, donate_label, start_button, stop_button, preview_button, live_button, Lang
    global use_folder_as_source_switch, use_folder_as_target_switch, keep_fps_checkbox, keep_frames_switch, enhancer_switch, keep_audio_switch, many_faces_switch, color_correction_switch
    ctk.deactivate_automatic_dpi_awareness()
    ctk.set_appearance_mode('system')
    ctk.set_default_color_theme(resolve_relative_path('ui.json'))

    root = ctk.CTk()
    root.minsize(ROOT_WIDTH, ROOT_HEIGHT)
    root.title(f'{modules.metadata.name} {modules.metadata.version} {modules.metadata.edition}')
    root.configure()
    root.protocol('WM_DELETE_WINDOW', lambda: destroy())

    source_label = ctk.CTkLabel(root, text=None)
    source_label.place(relx=0.1, rely=0.1, relwidth=0.3, relheight=0.25)

    target_label = ctk.CTkLabel(root, text=None)
    target_label.place(relx=0.6, rely=0.1, relwidth=0.3, relheight=0.25)

    select_face_button = ctk.CTkButton(root, text=Lang.SELECT_A_FACE, cursor='hand2', command=lambda: select_source_path())
    select_face_button.place(relx=0.1, rely=0.4, relwidth=0.3, relheight=0.1)

    swap_faces_button = ctk.CTkButton(root, text='↔', cursor='hand2', command=lambda: swap_faces_paths())
    swap_faces_button.place(relx=0.45, rely=0.4, relwidth=0.1, relheight=0.1)

    select_target_button = ctk.CTkButton(root, text=Lang.SELECT_A_TARGET, cursor='hand2', command=lambda: select_target_path())
    select_target_button.place(relx=0.6, rely=0.4, relwidth=0.3, relheight=0.1)

    use_folder_as_source = ctk.BooleanVar(value=modules.globals.use_source_folder)
    use_folder_as_source_switch = ctk.CTkSwitch(root, text=Lang.USE_FOLDER_AS_SOURCE, variable=use_folder_as_source, cursor='hand2', command=lambda: toggle_source_mode(use_folder_as_source.get()))
    use_folder_as_source_switch.place(relx=0.6, rely=0.55)

    use_folder_as_target = ctk.BooleanVar(value=modules.globals.use_target_folder)
    use_folder_as_target_switch = ctk.CTkSwitch(root, text=Lang.USE_FOLDER_AS_TARGET, variable=use_folder_as_target, cursor='hand2', command=lambda: toggle_target_mode(use_folder_as_target.get()))
    use_folder_as_target_switch.place(relx=0.6, rely=0.6)

    keep_fps_value = ctk.BooleanVar(value=modules.globals.keep_fps)
    keep_fps_checkbox = ctk.CTkSwitch(root, text=Lang.KEEP_FPS, variable=keep_fps_value, cursor='hand2', command=lambda: setattr(modules.globals, 'keep_fps', not modules.globals.keep_fps))
    keep_fps_checkbox.place(relx=0.1, rely=0.55)

    keep_frames_value = ctk.BooleanVar(value=modules.globals.keep_frames)
    keep_frames_switch = ctk.CTkSwitch(root, text=Lang.KEEP_FRAMES, variable=keep_frames_value, cursor='hand2', command=lambda: setattr(modules.globals, 'keep_frames', keep_frames_value.get()))
    keep_frames_switch.place(relx=0.1, rely=0.6)

    enhancer_value = ctk.BooleanVar(value=modules.globals.fp_ui['face_enhancer'])
    enhancer_switch = ctk.CTkSwitch(root, text=Lang.FACE_ENHANCER, variable=enhancer_value, cursor='hand2', command=lambda: update_tumbler('face_enhancer', enhancer_value.get()))
    enhancer_switch.place(relx=0.1, rely=0.65)

    keep_audio_value = ctk.BooleanVar(value=modules.globals.keep_audio)
    keep_audio_switch = ctk.CTkSwitch(root, text=Lang.KEEP_AUDIO, variable=keep_audio_value, cursor='hand2', command=lambda: setattr(modules.globals, 'keep_audio', keep_audio_value.get()))
    keep_audio_switch.place(relx=0.6, rely=0.65)

    many_faces_value = ctk.BooleanVar(value=modules.globals.many_faces)
    many_faces_switch = ctk.CTkSwitch(root, text=Lang.MANY_FACES, variable=many_faces_value, cursor='hand2', command=lambda: setattr(modules.globals, 'many_faces', many_faces_value.get()))
    many_faces_switch.place(relx=0.6, rely=0.7)

    color_correction_value = ctk.BooleanVar(value=modules.globals.color_correction)
    color_correction_switch = ctk.CTkSwitch(root, text=Lang.COLOR_CORRECTION, variable=color_correction_value, cursor='hand2', command=lambda: setattr(modules.globals, 'color_correction', color_correction_value.get()))
    color_correction_switch.place(relx=0.6, rely=0.75)

    start_button = ctk.CTkButton(root, text=Lang.START_PROCESS, cursor='hand2', command=lambda: select_output_path(start))
    start_button.place(relx=0.15, rely=0.80, relwidth=0.2, relheight=0.05)

    stop_button = ctk.CTkButton(root, text=Lang.DESTROY, cursor='hand2', command=lambda: destroy())
    stop_button.place(relx=0.4, rely=0.80, relwidth=0.2, relheight=0.05)

    preview_button = ctk.CTkButton(root, text=Lang.PREVIEW, cursor='hand2', command=lambda: toggle_preview())
    preview_button.place(relx=0.65, rely=0.80, relwidth=0.2, relheight=0.05)

    live_button = ctk.CTkButton(root, text=Lang.LIVE, cursor='hand2', command=lambda: webcam_preview())
    live_button.place(relx=0.40, rely=0.86, relwidth=0.2, relheight=0.05)
    
    change_language_button = ctk.CTkButton(root, text="Lang", cursor='hand2', command=change_language)
    change_language_button.place(relx=0.8, rely=0.86, relwidth=0.15, relheight=0.05)

    status_label = ctk.CTkLabel(root, text=None, justify='center')
    status_label.place(relx=0.1, rely=0.9, relwidth=0.8)

    donate_label = ctk.CTkLabel(root, text=Lang.DONATE, justify='center', cursor='hand2')
    donate_label.place(relx=0.1, rely=0.95, relwidth=0.8)
    donate_label.configure(text_color=ctk.ThemeManager.theme.get('URL').get('text_color'))
    donate_label.bind('<Button>', lambda event: webbrowser.open('https://paypal.me/hacksider'))

    return root

def create_preview(parent: ctk.CTkToplevel) -> ctk.CTkToplevel:
    global preview_label, preview_slider, Lang

    preview = ctk.CTkToplevel(parent)
    preview.withdraw()
    preview.title(Lang.PREVIEW)
    preview.configure()
    preview.protocol('WM_DELETE_WINDOW', lambda: toggle_preview())
    preview.resizable(width=True, height=True)

    preview_label = ctk.CTkLabel(preview, text=None)
    preview_label.pack(fill='both', expand=True)

    preview_slider = ctk.CTkSlider(preview, from_=0, to=100, number_of_steps=1, command=lambda val: update_preview(val))
    preview_slider.pack(fill='x', padx=10, pady=5)

    return preview


def update_status(text: str) -> None:
    status_label.configure(text=text)
    ROOT.update()

def update_tumbler(var: str, value: bool) -> None:
    modules.globals.fp_ui[var] = value

def select_source_path() -> None:
    global RECENT_DIRECTORY_SOURCE, img_ft

    PREVIEW.withdraw()
    if modules.globals.use_source_folder:
        folder_path = ctk.filedialog.askdirectory(title=Lang.SELECT_SOURCE_FOLDER, initialdir=RECENT_DIRECTORY_SOURCE)
        if folder_path:
            modules.globals.source_folder_path = folder_path
            RECENT_DIRECTORY_SOURCE = folder_path
            
    else:
        file_path = ctk.filedialog.askopenfilename(filetypes=[(Lang.SELECT_SOURCE_FILES, img_ft), (Lang.ALL_FILES, '*.*')], title=Lang.SELECT_SOURCE_FOLDER, initialdir=RECENT_DIRECTORY_SOURCE)
        if file_path:
            modules.globals.source_file_path = file_path
            RECENT_DIRECTORY_SOURCE = os.path.dirname(file_path)
            

def select_target_path() -> None:
    global RECENT_DIRECTORY_TARGET, vid_ft

    PREVIEW.withdraw()
    if modules.globals.use_target_folder:
        folder_path = ctk.filedialog.askdirectory(title=Lang.SELECT_TARGET_FOLDER, initialdir=RECENT_DIRECTORY_TARGET)
        if folder_path:
            modules.globals.target_folder_path = folder_path
            RECENT_DIRECTORY_TARGET = folder_path
            
    else:
        file_path = ctk.filedialog.askopenfilename(filetypes=[(Lang.SELECT_TARGET_FILES, vid_ft), (Lang.ALL_FILES, '*.*')], title=Lang.SELECT_TARGET_FOLDER, initialdir=RECENT_DIRECTORY_TARGET)
        if file_path:
            modules.globals.target_file_path = file_path
            RECENT_DIRECTORY_TARGET = os.path.dirname(file_path)
            

def select_output_path(start: Callable[[], None]) -> None:
    global RECENT_DIRECTORY_OUTPUT

    output_path = ctk.filedialog.askopenfilename(filetypes=[(Lang.SELECT_OUTPUT_FILES, vid_ft), (Lang.ALL_FILES, '*.*')], title=Lang.SELECT_OUTPUT_FOLDER, initialdir=RECENT_DIRECTORY_TARGET)
    if output_path:
        modules.globals.output_file_path = output_path
        RECENT_DIRECTORY_OUTPUT = os.path.dirname(output_path)
        start()

def toggle_source_mode(use_folder: bool) -> None:
    modules.globals.use_source_folder = use_folder

def toggle_target_mode(use_folder: bool) -> None:
    modules.globals.use_target_folder = use_folder

def toggle_preview() -> None:
    global PREVIEW

    if PREVIEW.state() == 'withdrawn':
        PREVIEW.deiconify()
    else:
        PREVIEW.withdraw()

def webcam_preview() -> None:
    global PREVIEW

    PREVIEW.withdraw()
    video_capture = cv2.VideoCapture(0)
    while True:
        ret, frame = video_capture.read()
        if not ret:
            break
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        preview_label.configure(image=ImageOps.fit(image, (PREVIEW_MAX_WIDTH, PREVIEW_MAX_HEIGHT)))
        ROOT.update()
    video_capture.release()


def update_preview(frame_number: int = 0) -> None:
    if modules.globals.source_path and modules.globals.target_path:
        update_status('Processing...')
        temp_frame = get_video_frame(modules.globals.target_path, frame_number)

        for frame_processor in get_frame_processors_modules(modules.globals.frame_processors):
            temp_frame = frame_processor.process_frame(
                get_one_face(cv2.imread(modules.globals.source_path)),
                temp_frame
            )
        image = Image.fromarray(cv2.cvtColor(temp_frame, cv2.COLOR_BGR2RGB))
        image = ImageOps.contain(image, (PREVIEW_MAX_WIDTH, PREVIEW_MAX_HEIGHT), Image.LANCZOS)
        image = ctk.CTkImage(image, size=image.size)
        preview_label.configure(image=image)
        update_status('Processing succeed!')
        PREVIEW.deiconify()


def swap_faces_paths() -> None:
    source_path = modules.globals.source_file_path
    target_path = modules.globals.target_file_path
    modules.globals.source_file_path = target_path
    modules.globals.target_file_path = source_path
    source_label.configure(text=os.path.basename(modules.globals.source_file_path))
    target_label.configure(text=os.path.basename(modules.globals.target_file_path))
import tkinter as tk
def change_language() -> None:
    global language_manager, Lang

    # Define available languages
    available_languages = [
        'English', 'Spanish', 'French', 'Arabic', 'Dutch', 'German',
        'Portuguese', 'Russian'
    ]  # Example languages

    def on_select_language():
        selected_language = language_var.get()
        if selected_language in available_languages:
            language_manager.set_language(selected_language.lower())
            global Lang
            Lang = language_manager.get_language()  # Update Lang with the new language
            update_ui_texts()  # Refresh UI texts based on the new language

    dialog = ctk.CTkToplevel(ROOT)
    dialog.title("Select Language")

    language_var = tk.StringVar(value=Lang)  # Use the current language as default
    
    tk.Label(dialog, text="Choose a language:").pack(padx=10, pady=10)

    for lang in available_languages:
        tk.Radiobutton(dialog, text=lang, variable=language_var, value=lang).pack(anchor='w', padx=10)

    tk.Button(dialog, text="OK", command=on_select_language).pack(pady=10)
def update_ui_texts() -> None:
    global source_label, target_label, status_label, donate_label, start_button, stop_button, preview_button, live_button, Lang
    
    # Ensure Lang is updated to reflect the new language
    Lang = language_manager.get_language()

    # Update text for all labels and buttons
    source_label.configure(text=Lang.SELECT_A_FACE)
    target_label.configure(text=Lang.SELECT_A_TARGET)
    status_label.configure(text='Switched language!')
    donate_label.configure(text=Lang.DONATE)
    start_button.configure(text=Lang.START_PROCESS)
    stop_button.configure(text=Lang.DESTROY)
    preview_button.configure(text=Lang.PREVIEW)
    live_button.configure(text=Lang.LIVE)
        # Update text for switches and other elements
def update_ui_texts() -> None:
    global source_label, target_label, status_label, donate_label, start_button, stop_button, preview_button, live_button, Lang
    global use_folder_as_source_switch, use_folder_as_target_switch, keep_fps_checkbox, keep_frames_switch, enhancer_switch, keep_audio_switch, many_faces_switch, color_correction_switch
    
    # Ensure Lang is updated to reflect the new language
    Lang = language_manager.get_language()

    # Update text for all labels and buttons
    source_label.configure(text=Lang.SELECT_A_FACE)
    target_label.configure(text=Lang.SELECT_A_TARGET)
    status_label.configure(text='Switched language!')
    donate_label.configure(text=Lang.DONATE)
    start_button.configure(text=Lang.START_PROCESS)
    stop_button.configure(text=Lang.DESTROY)
    preview_button.configure(text=Lang.PREVIEW)
    live_button.configure(text=Lang.LIVE)
    
    # Update text for switches and other elements
    use_folder_as_source_switch.configure(text=getattr(Lang, 'USE_FOLDER_AS_SOURCE', "Use Folder as Source"))
    use_folder_as_target_switch.configure(text=getattr(Lang, 'USE_FOLDER_AS_TARGET', "Use Folder as Target"))
    keep_fps_checkbox.configure(text=getattr(Lang, 'KEEP_FPS', "Keep FPS"))
    keep_frames_switch.configure(text=getattr(Lang, 'KEEP_FRAMES', "Keep Frames"))
    enhancer_switch.configure(text=getattr(Lang, 'FACE_ENHANCER', "Face Enhancer"))
    keep_audio_switch.configure(text=getattr(Lang, 'KEEP_AUDIO', "Keep Audio"))
    many_faces_switch.configure(text=getattr(Lang, 'MANY_FACES', "Many Faces"))
    color_correction_switch.configure(text=getattr(Lang, 'COLOR_CORRECTION', "Color Correction"))

