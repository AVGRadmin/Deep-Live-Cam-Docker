import os
import webbrowser
import customtkinter as ctk
from typing import Callable, Tuple
import cv2
from PIL import Image, ImageOps
import tkinter as tk
from PIL import Image, ImageOps
from customtkinter import CTkImage

import modules.globals
import modules.metadata
from modules.face_analyser import get_one_face
from modules.capturer import get_video_frame
from modules.processors.frame.core import get_frame_processors_modules
from modules.lang.manager import LanguageManager
from modules.utilities import resolve_relative_path, is_image, is_video

ROOT = None
ROOT_HEIGHT = 700
ROOT_WIDTH = 600

PREVIEW = None
PREVIEW_MAX_HEIGHT = 700    
PREVIEW_MAX_WIDTH  = 1200

RECENT_DIRECTORY_SOURCE = None
RECENT_DIRECTORY_TARGET = None
RECENT_DIRECTORY_OUTPUT = None

# UI Elements
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
use_folder_as_source_switch = None
use_folder_as_target_switch = None
keep_fps_checkbox = None
keep_frames_switch = None
enhancer_switch = None
keep_audio_switch = None
many_faces_switch = None
color_correction_switch = None
change_language_button=None
select_face_button=None
select_target_button=None

# Language vars
lang_dialog_open=None
language_manager = LanguageManager()
lm = language_manager.get_language()

vid_ft = [(lm.VIDEO_FILES, '*.mp4 *.mov')]
img_ft = [(lm.IMG_FILES, '*.png *.jpg *.jpeg')]
def init(start: Callable[[], None], destroy: Callable[[], None]) -> ctk.CTk:
    global ROOT, PREVIEW
    ROOT = create_root(start, destroy)
    return ROOT

def create_root(start: Callable[[], None], destroy: Callable[[], None]) -> ctk.CTk:
    global source_label, target_label, status_label, donate_label
    global start_button, stop_button, preview_button, live_button
    global use_folder_as_source_switch, use_folder_as_target_switch, keep_fps_checkbox
    global keep_frames_switch, enhancer_switch, keep_audio_switch, many_faces_switch
    global color_correction_switch, change_language_button, select_face_button, select_target_button

    ctk.deactivate_automatic_dpi_awareness()
    ctk.set_appearance_mode('system')
    ctk.set_default_color_theme(resolve_relative_path('ui.json'))

    root = ctk.CTk()
    root.minsize(ROOT_WIDTH, ROOT_HEIGHT)
    root.title(f'{modules.metadata.name} {modules.metadata.version} {modules.metadata.edition}')
    root.protocol('WM_DELETE_WINDOW', lambda: destroy())

    # Create and place UI elements using grid layout
    root.grid_rowconfigure([0, 1, 2, 3, 4, 5, 6, 7, 8], weight=1)
    root.grid_columnconfigure([0, 1, 2, 3], weight=1)

    source_label = ctk.CTkLabel(root, text=lm.SELECT_SOURCE_IMAGE, text_color='#000000', font=('Helvetica', 12))
    source_label.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')

    target_label = ctk.CTkLabel(root, text=lm.SELECT_TARGET_IMGVID, text_color='#000000', font=('Helvetica', 12))
    target_label.grid(row=0, column=2, padx=10, pady=10, sticky='nsew')

    select_face_button = ctk.CTkButton(root, text=lm.SELECT_DIALOG_SOURCE, cursor='hand2', command=select_source_path)
    select_face_button.grid(row=1, column=0, padx=10, pady=5, sticky='ew')

    swap_faces_button = ctk.CTkButton(root, text='↔', cursor='hand2', command=swap_faces_paths)
    swap_faces_button.grid(row=1, column=1, padx=10, pady=5, sticky='ew')

    select_target_button = ctk.CTkButton(root, text=lm.SELECT_DIALOG_TARGET, cursor='hand2', command=select_target_path)
    select_target_button.grid(row=1, column=2, padx=10, pady=5, sticky='ew')

    use_folder_as_source_switch = ctk.CTkSwitch(root, text=lm.USE_FOLDER_AS_SOURCE, command=lambda: toggle_source_mode(use_folder_as_source_switch.get()))
    use_folder_as_source_switch.grid(row=2, column=0, padx=10, pady=5, sticky='w')

    use_folder_as_target_switch = ctk.CTkSwitch(root, text=lm.USE_FOLDER_AS_TARGET, command=lambda: toggle_target_mode(use_folder_as_target_switch.get()))
    use_folder_as_target_switch.grid(row=2, column=2, padx=10, pady=5, sticky='w')

    keep_fps_checkbox = ctk.CTkSwitch(root, text=lm.KEEP_FPS, command=lambda: setattr(modules.globals, 'keep_fps', not modules.globals.keep_fps))
    keep_fps_checkbox.grid(row=3, column=0, padx=10, pady=5, sticky='w')

    keep_frames_switch = ctk.CTkSwitch(root, text=lm.KEEP_FRAMES, command=lambda: setattr(modules.globals, 'keep_frames', keep_frames_switch.get()))
    keep_frames_switch.grid(row=3, column=1, padx=10, pady=5, sticky='w')

    enhancer_switch = ctk.CTkSwitch(root, text=lm.FACE_ENHANCER, command=lambda: update_tumbler('face_enhancer', enhancer_switch.get()))
    enhancer_switch.grid(row=3, column=2, padx=10, pady=5, sticky='w')

    keep_audio_switch = ctk.CTkSwitch(root, text=lm.KEEP_AUDIO, command=lambda: setattr(modules.globals, 'keep_audio', keep_audio_switch.get()))
    keep_audio_switch.grid(row=4, column=0, padx=10, pady=5, sticky='w')

    many_faces_switch = ctk.CTkSwitch(root, text=lm.MANY_FACES, command=lambda: setattr(modules.globals, 'many_faces', many_faces_switch.get()))
    many_faces_switch.grid(row=4, column=1, padx=10, pady=5, sticky='w')

    color_correction_switch = ctk.CTkSwitch(root, text=lm.COLOR_CORRECTION, command=lambda: setattr(modules.globals, 'color_correction', color_correction_switch.get()))
    color_correction_switch.grid(row=4, column=2, padx=10, pady=5, sticky='w')

    start_button = ctk.CTkButton(root, text=lm.START_PROCESS, cursor='hand2', command=lambda: select_output_path(start))
    start_button.grid(row=5, column=0, padx=10, pady=10, sticky='ew')

    stop_button = ctk.CTkButton(root, text=lm.STOP_PROCESS, cursor='hand2', command=destroy)
    stop_button.grid(row=5, column=1, padx=10, pady=10, sticky='ew')

    preview_button = ctk.CTkButton(root, text=lm.PREVIEW, cursor='hand2', command=toggle_preview)
    preview_button.grid(row=5, column=2, padx=10, pady=10, sticky='ew')

    live_button = ctk.CTkButton(root, text=lm.LIVE, cursor='hand2', command=webcam_preview)
    live_button.grid(row=5, column=3, padx=10, pady=10, sticky='ew')

    change_language_button = ctk.CTkButton(root, text=lm.LANGUAGE_BUTTON, cursor='hand2', command=change_language)
    change_language_button.grid(row=6, column=3, padx=10, pady=10, sticky='ew')

    status_label = ctk.CTkLabel(root, text=None, justify='center', text_color='#000000', font=('Helvetica', 12))
    status_label.grid(row=7, column=0, columnspan=4, padx=10, pady=10, sticky='ew')

    donate_label = ctk.CTkLabel(root, text=lm.DONATE, justify='center', cursor='hand2', text_color=ctk.ThemeManager.theme.get('URL').get('text_color'))
    donate_label.grid(row=8, column=0, columnspan=4, padx=10, pady=10, sticky='ew')
    donate_label.bind('<Button>', lambda event: webbrowser.open('https://paypal.me/hacksider'))

    return root

def create_preview(parent: ctk.CTk) -> ctk.CTkToplevel:
    preview = ctk.CTkToplevel(parent)
    preview.title(lm.PREVIEW_TITLE)
    preview.geometry(f"{PREVIEW_MAX_WIDTH}x{PREVIEW_MAX_HEIGHT}")
    preview.protocol('WM_DELETE_WINDOW', lambda: close_preview(preview))
    preview.grid_rowconfigure(0, weight=1)
    preview.grid_columnconfigure(0, weight=1)

    global preview_label
    preview_label = ctk.CTkLabel(preview)
    preview_label.grid(row=0, column=0, sticky='nsew')
    preview_label.configure(text="")
    return preview

def update_ui_elements():
    global source_label, target_label, status_label, donate_label, start_button, stop_button, preview_button, live_button
    global use_folder_as_source_switch, use_folder_as_target_switch, keep_fps_checkbox, keep_frames_switch, enhancer_switch
    global keep_audio_switch, many_faces_switch, color_correction_switch, lm, change_language_button

    update_ui_texts()

def update_status(text: str) -> None:
    status_label.configure(text=text)
    ROOT.update()

def update_tumbler(var: str, value: bool) -> None:
    modules.globals.fp_ui[var] = value

def select_source_path() -> None:
    global PREVIEW, RECENT_DIRECTORY_SOURCE, img_ft

    if PREVIEW:  # Check if PREVIEW is not None before trying to withdraw
        PREVIEW.withdraw()

    if modules.globals.use_source_folder:
        folder_path = ctk.filedialog.askdirectory(title=lm.SELECT_DIALOG_SOURCE_FOLDER, initialdir=RECENT_DIRECTORY_SOURCE)
        if folder_path:
            modules.globals.source_folder_path = folder_path
            RECENT_DIRECTORY_SOURCE = folder_path
    else:
        file_path = ctk.filedialog.askopenfilename(filetypes=img_ft, title=lm.SELECT_DIALOG_SOURCE, initialdir=RECENT_DIRECTORY_SOURCE)
        if file_path:
            modules.globals.source_path = file_path
            RECENT_DIRECTORY_SOURCE = os.path.dirname(file_path)
            # Display thumbnail
            image = render_image_preview(file_path, (200, 200))
            source_label.configure(image=image)

def select_target_path() -> None:
    global RECENT_DIRECTORY_TARGET,img_ft, vid_ft

    if PREVIEW:  # Check if PREVIEW is not None before trying to withdraw
        PREVIEW.withdraw()

    if modules.globals.use_target_folder:
        folder_path = ctk.filedialog.askdirectory(title=lm.SELECT_DIALOG_TARGET_FOLDER, initialdir=RECENT_DIRECTORY_TARGET)
        if folder_path:
            modules.globals.target_folder_path = folder_path
            RECENT_DIRECTORY_TARGET = folder_path
    else:
        file_path = ctk.filedialog.askopenfilename(filetypes=img_ft+vid_ft, title=lm.SELECT_DIALOG_TARGET, initialdir=RECENT_DIRECTORY_TARGET)
        if file_path:
            modules.globals.target_path = file_path
            RECENT_DIRECTORY_TARGET = os.path.dirname(file_path)
            # Display thumbnail
            if is_image(file_path):
                image = render_image_preview(file_path, (200, 200))
                target_label.configure(image=image)
            elif is_video(file_path):
                video_frame = render_video_preview(file_path, (200, 200))
                target_label.configure(image=video_frame)


def select_output_path(start: Callable[[], None]) -> None:
    global RECENT_DIRECTORY_OUTPUT

    if modules.globals.use_source_folder or modules.globals.use_target_folder:
        file_path = ctk.filedialog.askdirectory(title=lm.SELECT_DIALOG_OUTPUT_FOLDER, initialdir=RECENT_DIRECTORY_SOURCE)
    else:  
        valid = False
        if is_image(modules.globals.target_path):
            file_path = ctk.filedialog.asksaveasfilename(filetypes=img_ft, title=lm.SELECT_DIALOG_OUTPUT_FILE, initialdir=RECENT_DIRECTORY_OUTPUT)
            valid = True
        if is_video(modules.globals.target_path):
            file_path = ctk.filedialog.asksaveasfilename(filetypes=vid_ft, title=lm.SELECT_DIALOG_OUTPUT_FILE, initialdir=RECENT_DIRECTORY_OUTPUT)
            valid = True
        
        if not valid:
            update_status("Error: No valid input target defined")
            return

    if file_path:
        modules.globals.output_path = file_path
        RECENT_DIRECTORY_OUTPUT = os.path.dirname(file_path)
        start()

def toggle_source_mode(use_folder: bool) -> None:
    modules.globals.use_source_folder = use_folder

def toggle_target_mode(use_folder: bool) -> None:
    modules.globals.use_target_folder = use_folder

def toggle_preview() -> None:
    global PREVIEW
    if PREVIEW is None:
        PREVIEW = create_preview(ROOT)
    else:
        if PREVIEW.state() == 'withdrawn':
            PREVIEW.deiconify()
        else:
            PREVIEW.withdraw()

def webcam_preview() -> None:
    global PREVIEW

    if PREVIEW is None:
        PREVIEW = create_preview(ROOT)
    else:
        if PREVIEW.state() == 'withdrawn':
            PREVIEW.deiconify()
        else:
            PREVIEW.withdraw()
    PREVIEW.withdraw()
    video_capture = cv2.VideoCapture(0)
    while True:
        ret, frame = video_capture.read()
        if not ret:
            break
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        image = ImageOps.fit(image, (PREVIEW_MAX_WIDTH, PREVIEW_MAX_HEIGHT))
        
         # Convert PIL image to PhotoImage
        tk_image = CTkImage(light_image=image, size=(PREVIEW_MAX_WIDTH, PREVIEW_MAX_HEIGHT))

        # Update the preview label with the PhotoImage
        preview_label.configure(image=tk_image)
        preview_label.image = tk_image 
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
    source_path = modules.globals.source_path
    target_path = modules.globals.target_path
    modules.globals.source_path = target_path
    modules.globals.target_path = source_path
    source_label.configure(text=os.path.basename(modules.globals.source_path))
    target_label.configure(text=os.path.basename(modules.globals.target_path))
    
def change_language() -> None:
    global language_manager, lm, lang_dialog_open
    # Prevent opening another dialog if one is already open
    if lang_dialog_open:
        return

    lang_dialog_open = True

    def on_select_language():
        selected_language = language_var.get()
        changed=False
        if selected_language in language_manager.available_languages:
            language_manager.set_language(selected_language.lower())
            global lm
            lm = language_manager.get_language()
            try:
                update_ui_texts()
                changed=True
            except Exception:
                changed=False
                update_status("Not supported!")
        if changed:
            close_dialog()

    def close_dialog():
        nonlocal dialog
        global lang_dialog_open
        lang_dialog_open = False
        dialog.destroy()

    dialog = ctk.CTkToplevel(ROOT)
    dialog.title("Select language")
    dialog.protocol("WM_DELETE_WINDOW", close_dialog)  

    language_var = tk.StringVar(value=lm)
    tk.Label(dialog, text="Choose a language:").pack(padx=10, pady=10)
    for lang in language_manager.available_languages:
        tk.Radiobutton(dialog, text=lang, variable=language_var, value=lang).pack(anchor='w', padx=10)
    tk.Button(dialog, text="OK", command=on_select_language).pack(pady=10)

def update_ui_texts() -> None:
    global source_label, target_label, status_label, donate_label, start_button, stop_button, preview_button, live_button, select_face_button, select_target_button, lm
    
    # Ensure lm is updated to reflect the new language
    lm = language_manager.get_language()

    # Labels
    source_label.configure(text=lm.SELECT_DIALOG_SOURCE)
    target_label.configure(text=lm.SELECT_DIALOG_TARGET)
    status_label.configure(text=lm.STATUS_LABEL)
    donate_label.configure(text=lm.DONATE)

    # Buttons
    start_button.configure(text=lm.START_PROCESS)
    stop_button.configure(text=lm.STOP_PROCESS)
    preview_button.configure(text=lm.PREVIEW)
    live_button.configure(text=lm.LIVE)
    change_language_button.configure(text=lm.LANGUAGE_BUTTON)
    select_face_button.configure(text=lm.SELECT_DIALOG_SOURCE)
    select_target_button.configure(text=lm.SELECT_DIALOG_TARGET)
    # Switches
    use_folder_as_source_switch.configure(text=lm.USE_FOLDER_AS_SOURCE)
    use_folder_as_target_switch.configure(text=lm.USE_FOLDER_AS_TARGET)
    keep_frames_switch.configure(text=lm.KEEP_FRAMES)
    enhancer_switch.configure(text=lm.FACE_ENHANCER)
    keep_audio_switch.configure(text=lm.KEEP_AUDIO)
    many_faces_switch.configure(text=lm.MANY_FACES)
    color_correction_switch.configure(text=lm.COLOR_CORRECTION)
    
    # Checkboxes
    keep_fps_checkbox.configure(text=lm.KEEP_FPS)

def close_preview(preview: ctk.CTkToplevel):
    preview.destroy()
    global PREVIEW
    PREVIEW = None

def render_image_preview(image_path: str, size: Tuple[int, int]) -> ctk.CTkImage:
    image = Image.open(image_path)
    image = ImageOps.fit(image, size, Image.LANCZOS)
    return ctk.CTkImage(image, size=image.size)

def render_video_preview(video_path: str, size: Tuple[int, int], frame_number: int = 0) -> ctk.CTkImage:
    capture = cv2.VideoCapture(video_path)
    if frame_number:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    has_frame, frame = capture.read()
    if has_frame:
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        image = ImageOps.fit(image, size, Image.LANCZOS)
        return ctk.CTkImage(image, size=image.size)
    capture.release()
    cv2.destroyAllWindows()
