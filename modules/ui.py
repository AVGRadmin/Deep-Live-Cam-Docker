import os
import webbrowser
import customtkinter as ctk
from typing import Callable, Tuple
import cv2
from PIL import Image, ImageOps
import tkinter as tk
from customtkinter import CTkImage

import modules.globals
import modules.metadata
from modules.face_analyser import get_one_face
from modules.capturer import get_video_frame
from modules.processors.frame.core import get_frame_processors_modules
from modules.lang.manager import LanguageManager
from modules.utilities import resolve_relative_path, is_image, is_video

# Global UI Variables
ROOT = None
PREVIEW = None
RECENT_DIRECTORY_SOURCE = None
RECENT_DIRECTORY_TARGET = None
RECENT_DIRECTORY_OUTPUT = None

lang_dialog_open=None
# Language Management
language_manager = LanguageManager()
lm = language_manager.get_language()

def init(start: Callable[[], None], destroy: Callable[[], None]) -> ctk.CTk:
    global ROOT
    ROOT = create_root(start, destroy)
    return ROOT

def create_root(start: Callable[[], None], destroy: Callable[[], None]) -> ctk.CTk:
    global ROOT

    # Setup UI root
    ctk.deactivate_automatic_dpi_awareness()
    ctk.set_appearance_mode('system')
    ctk.set_default_color_theme(resolve_relative_path('ui.json'))

    root = ctk.CTk()
    root.minsize(600, 700)
    root.title(f'{modules.metadata.name} {modules.metadata.version} {modules.metadata.edition}')
    root.protocol('WM_DELETE_WINDOW', lambda: destroy())

    # Configure grid layout
    configure_root_grid(root)

    # Create UI elements
    create_ui_elements(root, start, destroy)
    return root

def configure_root_grid(root: ctk.CTk) -> None:
    for i in range(9):
        root.grid_rowconfigure(i, weight=1)
    for i in range(4):
        root.grid_columnconfigure(i, weight=1)

def create_ui_elements(root: ctk.CTk, start: Callable[[], None], destroy: Callable[[], None]) -> None:
    global source_label, target_label, status_label, donate_label
    global start_button, stop_button, preview_button, live_button
    global use_folder_as_source_switch, use_folder_as_target_switch, keep_fps_checkbox
    global keep_frames_switch, enhancer_switch, keep_audio_switch, many_faces_switch
    global color_correction_switch, change_language_button, select_face_button, select_target_button

    # Labels
    source_label = ctk.CTkLabel(root, text=lm.SELECT_SOURCE_IMAGE, text_color='#000000', font=('Helvetica', 12))
    source_label.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')

    target_label = ctk.CTkLabel(root, text=lm.SELECT_TARGET_IMGVID, text_color='#000000', font=('Helvetica', 12))
    target_label.grid(row=0, column=2, padx=10, pady=10, sticky='nsew')

    status_label = ctk.CTkLabel(root, text=None, justify='center', text_color='#000000', font=('Helvetica', 12))
    status_label.grid(row=7, column=0, columnspan=4, padx=10, pady=10, sticky='ew')

    donate_label = create_donate_label(root)
    donate_label.grid(row=8, column=0, columnspan=4, padx=10, pady=10, sticky='ew')

    # Buttons
    select_face_button = ctk.CTkButton(root, text=lm.SELECT_DIALOG_SOURCE, cursor='hand2', command=select_source_path)
    select_face_button.grid(row=1, column=0, padx=10, pady=5, sticky='ew')

    swap_faces_button = ctk.CTkButton(root, text='↔', cursor='hand2', command=swap_faces_paths)
    swap_faces_button.grid(row=1, column=1, padx=10, pady=5, sticky='ew')

    select_target_button = ctk.CTkButton(root, text=lm.SELECT_DIALOG_TARGET, cursor='hand2', command=select_target_path)
    select_target_button.grid(row=1, column=2, padx=10, pady=5, sticky='ew')

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

    # Switches
    create_switches(root)

def create_donate_label(root: ctk.CTk) -> ctk.CTkLabel:
    label = ctk.CTkLabel(root, text=lm.DONATE, justify='center', cursor='hand2', text_color=ctk.ThemeManager.theme.get('URL').get('text_color'))
    label.bind('<Button>', lambda event: webbrowser.open('https://paypal.me/hacksider'))
    return label

def create_switches(root: ctk.CTk) -> None:
    global use_folder_as_source_switch, use_folder_as_target_switch, keep_fps_checkbox
    global keep_frames_switch, enhancer_switch, keep_audio_switch, many_faces_switch
    global color_correction_switch

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
    update_ui_elements_text()
    
def update_status(text: str) -> None:
    status_label.configure(text=text)
    ROOT.update()

def update_tumbler(var: str, value: bool) -> None:
    modules.globals.fp_ui[var] = value

def select_source_path() -> None:
    global PREVIEW, RECENT_DIRECTORY_SOURCE

    if PREVIEW:
        PREVIEW.withdraw()

    if modules.globals.use_source_folder:
        folder_path = ctk.filedialog.askdirectory(title=lm.SELECT_DIALOG_SOURCE_FOLDER, initialdir=RECENT_DIRECTORY_SOURCE)
        if folder_path:
            modules.globals.source_folder_path = folder_path
            RECENT_DIRECTORY_SOURCE = folder_path
    else:
        file_path = ctk.filedialog.askopenfilename(filetypes=[modules.globals.file_types[0]], title=lm.SELECT_DIALOG_SOURCE, initialdir=RECENT_DIRECTORY_SOURCE)
        if file_path:
            modules.globals.source_path = file_path
            RECENT_DIRECTORY_SOURCE = os.path.dirname(file_path)
            update_image_preview(source_label, file_path)

def select_target_path() -> None:
    global RECENT_DIRECTORY_TARGET

    if PREVIEW:
        PREVIEW.withdraw()

    if modules.globals.use_target_folder:
        folder_path = ctk.filedialog.askdirectory(title=lm.SELECT_DIALOG_TARGET_FOLDER, initialdir=RECENT_DIRECTORY_TARGET)
        if folder_path:
            modules.globals.target_folder_path = folder_path
            RECENT_DIRECTORY_TARGET = folder_path
    else:
        file_path = ctk.filedialog.askopenfilename(filetypes=modules.globals.file_types, title=lm.SELECT_DIALOG_TARGET, initialdir=RECENT_DIRECTORY_TARGET)
        if file_path:
            modules.globals.target_path = file_path
            RECENT_DIRECTORY_TARGET = os.path.dirname(file_path)
            update_target_preview(target_label, file_path)

def select_output_path(start: Callable[[], None]) -> None:
    global RECENT_DIRECTORY_OUTPUT

    file_path = select_output_path_dialog()
    if file_path:
        modules.globals.output_path = file_path
        RECENT_DIRECTORY_OUTPUT = os.path.dirname(file_path)
        start()

def select_output_path_dialog() -> str:
    if modules.globals.use_source_folder or modules.globals.use_target_folder:
        return ctk.filedialog.askdirectory(title=lm.SELECT_DIALOG_OUTPUT_FOLDER, initialdir=RECENT_DIRECTORY_SOURCE)
    
    valid = False
    file_path = None
    if is_image(modules.globals.target_path):
        file_path = ctk.filedialog.asksaveasfilename(filetypes=[modules.globals.file_types[0]], title=lm.SELECT_DIALOG_OUTPUT_FILE, initialdir=RECENT_DIRECTORY_OUTPUT)
        valid = True
    if is_video(modules.globals.target_path):
        file_path = ctk.filedialog.asksaveasfilename(filetypes=[modules.globals.file_types[1]], title=lm.SELECT_DIALOG_OUTPUT_FILE, initialdir=RECENT_DIRECTORY_OUTPUT)
        valid = True
    
    if not valid:
        update_status("Error: No valid input target defined")
    
    return file_path

    
def toggle_preview() -> None:
    global PREVIEW
    if PREVIEW is None:
        PREVIEW = create_preview(ROOT)
    else:
        if PREVIEW.state() == 'withdrawn':
            PREVIEW.deiconify()
        else:
            PREVIEW.withdraw()

def create_preview(parent: ctk.CTk) -> ctk.CTkToplevel:
    preview = ctk.CTkToplevel(parent)
    preview.title(lm.PREVIEW_TITLE)
    preview.geometry(f"1200x700")
    preview.protocol('WM_DELETE_WINDOW', lambda: close_preview(preview))
    preview.grid_rowconfigure(0, weight=1)
    preview.grid_columnconfigure(0, weight=1)

    global preview_label
    preview_label = ctk.CTkLabel(preview)
    preview_label.grid(row=0, column=0, sticky='nsew')
    preview_label.configure(text="")
    return preview

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
        update_webcam_frame(frame)
        ROOT.update()
    video_capture.release()

def update_webcam_frame(frame) -> None:
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    image = ImageOps.fit(image, (1200, 700))
    tk_image = CTkImage(light_image=image, size=(1200, 700))
    preview_label.configure(image=tk_image)
    preview_label.image = tk_image

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
        image = ImageOps.contain(image, (1200, 700), Image.LANCZOS)
        image = ctk.CTkImage(image, size=image.size)
        preview_label.configure(image=image)
        update_status('Processing succeed!')
        PREVIEW.deiconify()

def swap_faces_paths() -> None:
    modules.globals.source_path, modules.globals.target_path = modules.globals.target_path, modules.globals.source_path
    update_label_text(source_label, modules.globals.source_path)
    update_label_text(target_label, modules.globals.target_path)

def change_language() -> None:
    global lang_dialog_open
    if lang_dialog_open:
        return

    lang_dialog_open = True
    dialog = create_language_dialog()

def create_language_dialog() -> ctk.CTkToplevel:
    def on_select_language():
        selected_language = language_var.get()
        if selected_language in language_manager.language_modules:
            language_manager.set_language(selected_language.lower())
            update_ui_elements_text()
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
    for lang in language_manager.language_modules:
        tk.Radiobutton(dialog, text=lang, variable=language_var, value=lang).pack(anchor='w', padx=10)
    tk.Button(dialog, text="OK", command=on_select_language).pack(pady=10)
    return dialog

def update_ui_elements_text() -> None:
    global lm
    lm = language_manager.get_language()

    # Toggle first, update status label after
    toggle_source_mode(modules.globals.use_source_folder)
    toggle_target_mode(modules.globals.use_target_folder)
    
    status_label.configure(text=lm.WELCOME_LABEL)
    donate_label.configure(text=lm.DONATE)

    start_button.configure(text=lm.START_PROCESS)
    stop_button.configure(text=lm.STOP_PROCESS)
    preview_button.configure(text=lm.PREVIEW)
    live_button.configure(text=lm.LIVE)
    change_language_button.configure(text=lm.LANGUAGE_BUTTON)

    use_folder_as_source_switch.configure(text=lm.USE_FOLDER_AS_SOURCE)
    use_folder_as_target_switch.configure(text=lm.USE_FOLDER_AS_TARGET)
    keep_frames_switch.configure(text=lm.KEEP_FRAMES)
    enhancer_switch.configure(text=lm.FACE_ENHANCER)
    keep_audio_switch.configure(text=lm.KEEP_AUDIO)
    many_faces_switch.configure(text=lm.MANY_FACES)
    color_correction_switch.configure(text=lm.COLOR_CORRECTION)
    keep_fps_checkbox.configure(text=lm.KEEP_FPS)

def toggle_source_mode(use_folder: bool) -> None:
    modules.globals.use_source_folder = use_folder
    if use_folder:
        select_face_button.configure(text=lm.SELECT_DIALOG_SOURCE_FOLDER)
        source_label.configure(text=lm.SELECT_DIALOG_SOURCE_FOLDER)
        status_label.configure(text=lm.SOURCE_ITEM_FOLDER_STATUS_LABEL)
    else:
        select_face_button.configure(text=lm.SELECT_DIALOG_SOURCE)
        source_label.configure(text=lm.SELECT_DIALOG_SOURCE)
        status_label.configure(text=lm.SOURCE_ITEM_STATUS_LABEL)
 
def toggle_target_mode(use_folder: bool) -> None:
    modules.globals.use_target_folder = use_folder
    if use_folder:
        select_target_button.configure(text=lm.SELECT_DIALOG_TARGET_FOLDER)
        target_label.configure(text=lm.SELECT_DIALOG_TARGET_FOLDER)
        status_label.configure(text=lm.TARGET_ITEM_FOLDER_STATUS_LABEL)
    else:
        select_target_button.configure(text=lm.SELECT_DIALOG_TARGET)
        target_label.configure(text=lm.SELECT_DIALOG_TARGET)
        status_label.configure(text=lm.TARGET_ITEM_STATUS_LABEL)
def update_image_preview(label: ctk.CTkLabel, image_path: str) -> None:
    image = Image.open(image_path)
    image = ImageOps.fit(image, (200, 200), Image.LANCZOS)
    label.configure(image=ctk.CTkImage(image, size=(200, 200)))

def update_target_preview(label: ctk.CTkLabel, file_path: str) -> None:
    if is_image(file_path):
        update_image_preview(label, file_path)
    elif is_video(file_path):
        update_video_preview(label, file_path)

def update_video_preview(label: ctk.CTkLabel, video_path: str, frame_number: int = 0) -> None:
    capture = cv2.VideoCapture(video_path)
    if frame_number:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    has_frame, frame = capture.read()
    if has_frame:
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        image = ImageOps.fit(image, (200, 200), Image.LANCZOS)
        label.configure(image=ctk.CTkImage(image, size=(200, 200)))
    capture.release()
    cv2.destroyAllWindows()

def update_label_text(label: ctk.CTkLabel, path: str) -> None:
    label.configure(text=os.path.basename(path))

def close_preview(preview: ctk.CTkToplevel) -> None:
    preview.destroy()
    global PREVIEW
    PREVIEW = None
