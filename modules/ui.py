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
from modules.face_analyser import get_one_face, get_unique_faces_from_target_image, get_unique_faces_from_target_video, add_blank_map, has_valid_map, simplify_maps
from modules.capturer import get_video_frame, get_video_frame_total
from modules.processors.frame.core import get_frame_processors_modules
from modules.lang.manager import LanguageManager
from modules.utilities import resolve_relative_path, is_image, is_video

# Global UI Variables
ROOT = None
POPUP = None
POPUP_LIVE = None
ROOT_HEIGHT = 700
ROOT_WIDTH = 600

PREVIEW = None
PREVIEW_MAX_HEIGHT = 700
PREVIEW_MAX_WIDTH  = 1200
PREVIEW_DEFAULT_WIDTH  = 960
PREVIEW_DEFAULT_HEIGHT = 540

POPUP_WIDTH = 750
POPUP_HEIGHT = 810
POPUP_SCROLL_WIDTH = 740, 
POPUP_SCROLL_HEIGHT = 700

POPUP_LIVE_WIDTH = 900
POPUP_LIVE_HEIGHT = 820
POPUP_LIVE_SCROLL_WIDTH = 890, 
POPUP_LIVE_SCROLL_HEIGHT = 700

MAPPER_PREVIEW_MAX_HEIGHT = 100
MAPPER_PREVIEW_MAX_WIDTH = 100

DEFAULT_BUTTON_WIDTH = 200
DEFAULT_BUTTON_HEIGHT = 40

RECENT_DIRECTORY_SOURCE = None
RECENT_DIRECTORY_TARGET = None
RECENT_DIRECTORY_OUTPUT = None

preview_label = None
preview_slider = None
source_label = None
target_label = None
status_label = None
popup_status_label = None
popup_status_label_live = None
source_label_dict = {}
source_label_dict_live = {}
target_label_dict_live = {}
lang_dialog_open=None
# Language Management
language_manager = LanguageManager()
lm = language_manager.get_language()


img_ft, vid_ft = modules.globals.file_types

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

def analyze_target(start: Callable[[], None], root: ctk.CTk):
    if POPUP != None and POPUP.winfo_exists():
        update_status("Please complete pop-up or close it.")
        return

    if modules.globals.map_faces:
        modules.globals.souce_target_map = []

        if is_image(modules.globals.target_path):
            update_status('Getting unique faces')
            get_unique_faces_from_target_image()
        elif is_video(modules.globals.target_path):
            update_status('Getting unique faces')
            get_unique_faces_from_target_video()

        if len(modules.globals.souce_target_map) > 0:
            create_source_target_popup(start, root, modules.globals.souce_target_map)
        else:
            update_status("No faces found in target")
    else:
        select_output_path(start)

def create_source_target_popup(start: Callable[[], None], root: ctk.CTk, map: list) -> None:
    global POPUP, popup_status_label

    POPUP = ctk.CTkToplevel(root)
    POPUP.title("Source x Target Mapper")
    POPUP.geometry(f"{POPUP_WIDTH}x{POPUP_HEIGHT}")
    POPUP.focus()

    def on_submit_click(start):
        if has_valid_map():
            POPUP.destroy()
            select_output_path(start)
        else:
            update_pop_status("Atleast 1 source with target is required!")

    scrollable_frame = ctk.CTkScrollableFrame(POPUP, width=POPUP_SCROLL_WIDTH, height=POPUP_SCROLL_HEIGHT)
    scrollable_frame.grid(row=0, column=0, padx=0, pady=0, sticky='nsew')

    def on_button_click(map, button_num):
        map = update_popup_source(scrollable_frame, map, button_num)

    for item in map:
        id = item['id']

        button = ctk.CTkButton(scrollable_frame, text="Select source image", command=lambda id=id: on_button_click(map, id), width=DEFAULT_BUTTON_WIDTH, height=DEFAULT_BUTTON_HEIGHT)
        button.grid(row=id, column=0, padx=50, pady=10)

        x_label = ctk.CTkLabel(scrollable_frame, text=f"X", width=MAPPER_PREVIEW_MAX_WIDTH, height=MAPPER_PREVIEW_MAX_HEIGHT)
        x_label.grid(row=id, column=2, padx=10, pady=10)

        image = Image.fromarray(cv2.cvtColor(item['target']['cv2'], cv2.COLOR_BGR2RGB))
        image = image.resize((MAPPER_PREVIEW_MAX_WIDTH, MAPPER_PREVIEW_MAX_HEIGHT), Image.LANCZOS)
        tk_image = ctk.CTkImage(image, size=image.size)

        target_image = ctk.CTkLabel(scrollable_frame, text=f"T-{id}", width=MAPPER_PREVIEW_MAX_WIDTH, height=MAPPER_PREVIEW_MAX_HEIGHT)
        target_image.grid(row=id, column=3, padx=10, pady=10)
        target_image.configure(image=tk_image)

    popup_status_label = ctk.CTkLabel(POPUP, text=None, justify='center')
    popup_status_label.grid(row=1, column=0, pady=15)

    close_button = ctk.CTkButton(POPUP, text="Submit", command=lambda: on_submit_click(start))
    close_button.grid(row=2, column=0, pady=10)


def update_popup_source(scrollable_frame: ctk.CTkScrollableFrame, map: list, button_num: int) -> list:
    global source_label_dict

    source_path = ctk.filedialog.askopenfilename(title='select an source image', initialdir=RECENT_DIRECTORY_SOURCE, filetypes=[img_ft])

    if "source" in map[button_num]:
        map[button_num].pop("source")
        source_label_dict[button_num].destroy()
        del source_label_dict[button_num]
        
    if source_path == "":
        return map
    else:
        cv2_img = cv2.imread(source_path)
        face = get_one_face(cv2_img)

        if face:
            x_min, y_min, x_max, y_max = face['bbox']

            map[button_num]['source'] = {
                'cv2' : cv2_img[int(y_min):int(y_max), int(x_min):int(x_max)],
                'face' : face
                }
            
            image = Image.fromarray(cv2.cvtColor(map[button_num]['source']['cv2'], cv2.COLOR_BGR2RGB))
            image = image.resize((MAPPER_PREVIEW_MAX_WIDTH, MAPPER_PREVIEW_MAX_HEIGHT), Image.LANCZOS)
            tk_image = ctk.CTkImage(image, size=image.size)
            
            source_image = ctk.CTkLabel(scrollable_frame, text=f"S-{button_num}", width=MAPPER_PREVIEW_MAX_WIDTH, height=MAPPER_PREVIEW_MAX_HEIGHT)
            source_image.grid(row=button_num, column=1, padx=10, pady=10)
            source_image.configure(image=tk_image)
            source_label_dict[button_num] = source_image
        else:
            update_pop_status("Face could not be detected in last upload!")
        return map

def configure_root_grid(root: ctk.CTk) -> None:
    for i in range(9):
        root.grid_rowconfigure(i, weight=1)
    for i in range(4):
        root.grid_columnconfigure(i, weight=1)

def update_status(text: str) -> None:
    status_label.configure(text=text)
    ROOT.update()

def update_pop_status(text: str) -> None:
    popup_status_label.configure(text=text)

def update_pop_live_status(text: str) -> None:
    popup_status_label_live.configure(text=text)
def update_tumbler(var: str, value: bool) -> None:
    modules.globals.fp_ui[var] = value

def toggle_preview() -> None:
    global PREVIEW
    if PREVIEW is None:
        PREVIEW = create_preview(ROOT)
    else:
        if PREVIEW.state() == 'withdrawn':
            PREVIEW.deiconify()
        else:
            PREVIEW.withdraw()
            
def create_label(topLVL: ctk.CTkToplevel) -> ctk.CTkLabel:
    global preview_label
    preview_label = ctk.CTkLabel(ctk.CTkToplevel(topLVL))
    preview_label.grid(row=0, column=0, sticky='nsew')
    preview_label.configure(text="")
    return preview_label

def create_preview(parent: ctk.CTk) -> ctk.CTkToplevel:
    preview = ctk.CTkToplevel(parent)
    preview.title(lm.UI_WINDOW_PREVIEW_TITLE)
    preview.geometry(f"1200x700")
    preview.protocol('WM_DELETE_WINDOW', lambda: close_preview(preview))
    preview.grid_rowconfigure(0, weight=1)
    preview.grid_columnconfigure(0, weight=1)
    create_label(preview)
    return preview

def webcam_preview_old() -> None:
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

        
def update_image_preview(label: ctk.CTkLabel, image_path: str) -> None:
    image = Image.open(image_path)
    image = ImageOps.fit(image, (200, 200), Image.LANCZOS)
    label.configure(image=ctk.CTkImage(image, size=(200, 200)))



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
        
def webcam_preview(root: ctk.CTk):
    update_status("Opening webcam")
    if not modules.globals.map_faces:
        if modules.globals.source_path is None:
            # No image selected
            return
        
        create_webcam_preview(root)
    else:
        modules.globals.souce_target_map = []
        create_source_target_popup_for_webcam(root, modules.globals.souce_target_map)

def create_webcam_preview(root: ctk.CTk):
    if modules.globals.source_path is None:
        update_status("No source image selected!")
        return

    global preview_label, PREVIEW

    camera = cv2.VideoCapture(0)                                    # Use index for the webcam (adjust the index accordingly if necessary)    
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, PREVIEW_DEFAULT_WIDTH)     # Set the width of the resolution
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, PREVIEW_DEFAULT_HEIGHT)   # Set the height of the resolution
    camera.set(cv2.CAP_PROP_FPS, 60)                                # Set the frame rate of the webcam
    if not preview_label:
        PREVIEW=create_preview(root)
        preview_label= create_label(PREVIEW)
    preview_label.configure(width=PREVIEW_DEFAULT_WIDTH, height=PREVIEW_DEFAULT_HEIGHT)  # Reset the preview image before startup

    PREVIEW.deiconify()  # Open preview window

    frame_processors = get_frame_processors_modules(modules.globals.frame_processors)

    source_image = None  # Initialize variable for the selected face image

    while camera:
        ret, frame = camera.read()
        if not ret:
            break

        # Select and save face image only once
        if source_image is None and modules.globals.source_path:
            source_image = get_one_face(cv2.imread(modules.globals.source_path))

        temp_frame = frame.copy()  #Create a copy of the frame

        if modules.globals.live_mirror:
            temp_frame = cv2.flip(temp_frame, 1) # horizontal flipping

        if modules.globals.live_resizable:
            temp_frame = fit_image_to_size(temp_frame, PREVIEW.winfo_width(), PREVIEW.winfo_height())

        for frame_processor in frame_processors:
            temp_frame = frame_processor.process_frame(source_image, temp_frame)

        image = cv2.cvtColor(temp_frame, cv2.COLOR_BGR2RGB)  # Convert the image to RGB format to display it with Tkinter
        image = Image.fromarray(image)
        image = ImageOps.contain(image, (temp_frame.shape[1], temp_frame.shape[0]), Image.LANCZOS)
        image = ctk.CTkImage(image, size=image.size)
        preview_label.configure(image=image)
        ROOT.update()

        if PREVIEW.state() == 'withdrawn':
            break

    camera.release()
    PREVIEW.withdraw()  # Close preview window when loop is finished


def fit_image_to_size(image, width: int, height: int):
    if width is None and height is None:
      return image
    h, w, _ = image.shape
    ratio_h = 0.0
    ratio_w = 0.0
    if width > height:
        ratio_h = height / h
    else:
        ratio_w = width  / w
    ratio = max(ratio_w, ratio_h)
    new_size = (int(ratio * w), int(ratio * h))
    return cv2.resize(image, dsize=new_size)


def create_source_target_popup_for_webcam(root: ctk.CTk, map: list) -> None:
    global POPUP_LIVE, popup_status_label_live

    POPUP_LIVE = ctk.CTkToplevel(root)
    POPUP_LIVE.title("Source x Target Mapper")
    POPUP_LIVE.geometry(f"{POPUP_LIVE_WIDTH}x{POPUP_LIVE_HEIGHT}")
    POPUP_LIVE.focus()

    def on_submit_click():
        if has_valid_map():
            POPUP_LIVE.destroy()
            simplify_maps()
            create_webcam_preview()
        else:
            update_pop_live_status("Atleast 1 source with target is required!")

    def on_add_click():
        add_blank_map()
        refresh_data(map)
        update_pop_live_status("Please provide mapping!")

    popup_status_label_live = ctk.CTkLabel(POPUP_LIVE, text=None, justify='center')
    popup_status_label_live.grid(row=1, column=0, pady=15)

    add_button = ctk.CTkButton(POPUP_LIVE, text="Add", command=lambda: on_add_click())
    add_button.place(relx=0.2, rely=0.92, relwidth=0.2, relheight=0.05)

    
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

def update_webcam_source(scrollable_frame: ctk.CTkScrollableFrame, map: list, button_num: int) -> list:
    global source_label_dict_live

    source_path = ctk.filedialog.askopenfilename(title='select an source image', initialdir=RECENT_DIRECTORY_SOURCE, filetypes=[img_ft])

    if "source" in map[button_num]:
        map[button_num].pop("source")
        source_label_dict_live[button_num].destroy()
        del source_label_dict_live[button_num]
        
    if source_path == "":
        return map
    else:
        cv2_img = cv2.imread(source_path)
        face = get_one_face(cv2_img)

        if face:
            x_min, y_min, x_max, y_max = face['bbox']

            map[button_num]['source'] = {
                'cv2' : cv2_img[int(y_min):int(y_max), int(x_min):int(x_max)],
                'face' : face
                }
            
            image = Image.fromarray(cv2.cvtColor(map[button_num]['source']['cv2'], cv2.COLOR_BGR2RGB))
            image = image.resize((MAPPER_PREVIEW_MAX_WIDTH, MAPPER_PREVIEW_MAX_HEIGHT), Image.LANCZOS)
            tk_image = ctk.CTkImage(image, size=image.size)
            
            source_image = ctk.CTkLabel(scrollable_frame, text=f"S-{button_num}", width=MAPPER_PREVIEW_MAX_WIDTH, height=MAPPER_PREVIEW_MAX_HEIGHT)
            source_image.grid(row=button_num, column=1, padx=10, pady=10)
            source_image.configure(image=tk_image)
            source_label_dict_live[button_num] = source_image
        else:
            update_pop_live_status("Face could not be detected in last upload!")
        return map
    
def refresh_data(map: list):
    global POPUP_LIVE

    scrollable_frame = ctk.CTkScrollableFrame(POPUP_LIVE, width=POPUP_LIVE_SCROLL_WIDTH, height=POPUP_LIVE_SCROLL_HEIGHT)
    scrollable_frame.grid(row=0, column=0, padx=0, pady=0, sticky='nsew')

    def on_sbutton_click(map, button_num):
        map = update_webcam_source(scrollable_frame, map, button_num)

    def on_tbutton_click(map, button_num):
        map = update_webcam_target(scrollable_frame, map, button_num)

    for item in map:
        id = item['id']

        button = ctk.CTkButton(scrollable_frame, text="Select source image", command=lambda id=id: on_sbutton_click(map, id), width=DEFAULT_BUTTON_WIDTH, height=DEFAULT_BUTTON_HEIGHT)
        button.grid(row=id, column=0, padx=30, pady=10)

        x_label = ctk.CTkLabel(scrollable_frame, text=f"X", width=MAPPER_PREVIEW_MAX_WIDTH, height=MAPPER_PREVIEW_MAX_HEIGHT)
        x_label.grid(row=id, column=2, padx=10, pady=10)

        button = ctk.CTkButton(scrollable_frame, text="Select target image", command=lambda id=id: on_tbutton_click(map, id), width=DEFAULT_BUTTON_WIDTH, height=DEFAULT_BUTTON_HEIGHT)
        button.grid(row=id, column=3, padx=20, pady=10)

        if "source" in item:
            image = Image.fromarray(cv2.cvtColor(item['source']['cv2'], cv2.COLOR_BGR2RGB))
            image = image.resize((MAPPER_PREVIEW_MAX_WIDTH, MAPPER_PREVIEW_MAX_HEIGHT), Image.LANCZOS)
            tk_image = ctk.CTkImage(image, size=image.size)

            source_image = ctk.CTkLabel(scrollable_frame, text=f"S-{id}", width=MAPPER_PREVIEW_MAX_WIDTH, height=MAPPER_PREVIEW_MAX_HEIGHT)
            source_image.grid(row=id, column=1, padx=10, pady=10)
            source_image.configure(image=tk_image)

        if "target" in item:
            image = Image.fromarray(cv2.cvtColor(item['target']['cv2'], cv2.COLOR_BGR2RGB))
            image = image.resize((MAPPER_PREVIEW_MAX_WIDTH, MAPPER_PREVIEW_MAX_HEIGHT), Image.LANCZOS)
            tk_image = ctk.CTkImage(image, size=image.size)

            target_image = ctk.CTkLabel(scrollable_frame, text=f"T-{id}", width=MAPPER_PREVIEW_MAX_WIDTH, height=MAPPER_PREVIEW_MAX_HEIGHT)
            target_image.grid(row=id, column=4, padx=20, pady=10)
            target_image.configure(image=tk_image)
            
def update_webcam_target(scrollable_frame: ctk.CTkScrollableFrame, map: list, button_num: int) -> list:
    global target_label_dict_live

    target_path = ctk.filedialog.askopenfilename(title='select an target image', initialdir=RECENT_DIRECTORY_SOURCE, filetypes=[img_ft])

    if "target" in map[button_num]:
        map[button_num].pop("target")
        target_label_dict_live[button_num].destroy()
        del target_label_dict_live[button_num]
        
    if target_path == "":
        return map
    else:
        cv2_img = cv2.imread(target_path)
        face = get_one_face(cv2_img)

        if face:
            x_min, y_min, x_max, y_max = face['bbox']

            map[button_num]['target'] = {
                'cv2' : cv2_img[int(y_min):int(y_max), int(x_min):int(x_max)],
                'face' : face
                }
            
            image = Image.fromarray(cv2.cvtColor(map[button_num]['target']['cv2'], cv2.COLOR_BGR2RGB))
            image = image.resize((MAPPER_PREVIEW_MAX_WIDTH, MAPPER_PREVIEW_MAX_HEIGHT), Image.LANCZOS)
            tk_image = ctk.CTkImage(image, size=image.size)
            
            target_image = ctk.CTkLabel(scrollable_frame, text=f"T-{button_num}", width=MAPPER_PREVIEW_MAX_WIDTH, height=MAPPER_PREVIEW_MAX_HEIGHT)
            target_image.grid(row=button_num, column=4, padx=20, pady=10)
            target_image.configure(image=tk_image)
            target_label_dict_live[button_num] = target_image
        else:
            update_pop_live_status("Face could not be detected in last upload!")
        return map
    
    
    
def create_ui_elements(root: ctk.CTk, start: Callable[[], None], destroy: Callable[[], None]) -> None:
    global source_label, target_label, status_label, donate_label
    global start_button, stop_button, preview_button, live_button
    global use_folder_as_source_switch, use_folder_as_target_switch, keep_fps_checkbox
    global keep_frames_switch, enhancer_switch, keep_audio_switch, many_faces_switch
    global color_correction_switch, change_language_button, select_face_button, select_target_button

    # Labels
    source_label = ctk.CTkLabel(root, text=lm.UI_LABEL_SOURCE_FILE_TEXT, text_color='#000000', font=('Helvetica', 12))
    source_label.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')

    target_label = ctk.CTkLabel(root, text=lm.UI_LABEL_TARGET_FILE_TEXT, text_color='#000000', font=('Helvetica', 12))
    target_label.grid(row=0, column=2, padx=10, pady=10, sticky='nsew')

    status_label = ctk.CTkLabel(root, text=None, justify='center', text_color='#000000', font=('Helvetica', 12))
    status_label.grid(row=7, column=0, columnspan=4, padx=10, pady=10, sticky='ew')

    donate_label = create_donate_label(root)
    donate_label.grid(row=8, column=0, columnspan=4, padx=10, pady=10, sticky='ew')

    # Buttons
    select_face_button = ctk.CTkButton(root, text=lm.UI_BUTTON_SELECT, cursor='hand2', command=select_source_path)
    select_face_button.grid(row=1, column=0, padx=10, pady=5, sticky='ew')

    swap_faces_button = ctk.CTkButton(root, text='↔', cursor='hand2', command=swap_faces_paths)
    swap_faces_button.grid(row=1, column=1, padx=10, pady=5, sticky='ew')

    select_target_button = ctk.CTkButton(root, text=lm.UI_BUTTON_SELECT, cursor='hand2', command=select_target_path)
    select_target_button.grid(row=1, column=2, padx=10, pady=5, sticky='ew')

    start_button = ctk.CTkButton(root, text=lm.UI_BUTTON_START_PROCESS, cursor='hand2', command=lambda: select_output_path(start))
    start_button.grid(row=5, column=0, padx=10, pady=10, sticky='ew')

    stop_button = ctk.CTkButton(root, text=lm.UI_BUTTON_STOP_PROCESS, cursor='hand2', command=destroy)
    stop_button.grid(row=5, column=1, padx=10, pady=10, sticky='ew')

    preview_button = ctk.CTkButton(root, text=lm.UI_BUTTON_PREVIEW, cursor='hand2', command=toggle_preview)
    preview_button.grid(row=5, column=2, padx=10, pady=10, sticky='ew')
    live_button = ctk.CTkButton(root, text=lm.UI_BUTTON_LIVE, cursor='hand2', command=lambda: webcam_preview(root))
    #live_button = ctk.CTkButton(root, text=lm.LIVE, cursor='hand2', command=webcam_preview)
    live_button.grid(row=5, column=3, padx=10, pady=10, sticky='ew')

    change_language_button = ctk.CTkButton(root, text=lm.UI_BUTTON_LANGUAGE, cursor='hand2', command=change_language)
    change_language_button.grid(row=6, column=3, padx=10, pady=10, sticky='ew')
    map_faces = ctk.BooleanVar(value=modules.globals.map_faces)
    map_faces_switch = ctk.CTkSwitch(root, text='Map faces', variable=map_faces, cursor='hand2', command=lambda: setattr(modules.globals, 'map_faces', map_faces.get()))
    map_faces_switch.place(relx=0.1, rely=0.75)

    start_button = ctk.CTkButton(root, text='Start', cursor='hand2', command=lambda: analyze_target(start, root))
    
    # Switches
    create_switches(root)

def create_donate_label(root: ctk.CTk) -> ctk.CTkLabel:
    label = ctk.CTkLabel(root, text=lm.UI_BUTTON_DONATE, justify='center', cursor='hand2', text_color=ctk.ThemeManager.theme.get('URL').get('text_color'))
    label.bind('<Button>', lambda event: webbrowser.open('https://paypal.me/hacksider'))
    return label

def create_switches(root: ctk.CTk) -> None:
    global use_folder_as_source_switch, use_folder_as_target_switch, keep_fps_checkbox
    global keep_frames_switch, enhancer_switch, keep_audio_switch, many_faces_switch
    global color_correction_switch

    use_folder_as_source_switch = ctk.CTkSwitch(root, text=lm.UI_LABEL_USE_FOLDER_AS_SOURCE, command=lambda: toggle_source_mode(use_folder_as_source_switch.get()))
    use_folder_as_source_switch.grid(row=2, column=0, padx=10, pady=5, sticky='w')

    use_folder_as_target_switch = ctk.CTkSwitch(root, text=lm.UI_LABEL_USE_FOLDER_AS_TARGET, command=lambda: toggle_target_mode(use_folder_as_target_switch.get()))
    use_folder_as_target_switch.grid(row=2, column=2, padx=10, pady=5, sticky='w')

    keep_fps_checkbox = ctk.CTkSwitch(root, text=lm.UI_LABEL_KEEP_FPS, command=lambda: setattr(modules.globals, 'keep_fps', not modules.globals.keep_fps))
    keep_fps_checkbox.grid(row=3, column=0, padx=10, pady=5, sticky='w')

    keep_frames_switch = ctk.CTkSwitch(root, text=lm.UI_LABEL_KEEP_FRAMES, command=lambda: setattr(modules.globals, 'keep_frames', keep_frames_switch.get()))
    keep_frames_switch.grid(row=3, column=1, padx=10, pady=5, sticky='w')

    enhancer_switch = ctk.CTkSwitch(root, text=lm.UI_LABEL_FACE_ENHANCER, command=lambda: update_tumbler('face_enhancer', enhancer_switch.get()))
    enhancer_switch.grid(row=3, column=2, padx=10, pady=5, sticky='w')

    keep_audio_switch = ctk.CTkSwitch(root, text=lm.UI_LABEL_KEEP_AUDIO, command=lambda: setattr(modules.globals, 'keep_audio', keep_audio_switch.get()))
    keep_audio_switch.grid(row=4, column=0, padx=10, pady=5, sticky='w')

    many_faces_switch = ctk.CTkSwitch(root, text=lm.UI_LABEL_MANY_FACES, command=lambda: setattr(modules.globals, 'many_faces', many_faces_switch.get()))
    many_faces_switch.grid(row=4, column=1, padx=10, pady=5, sticky='w')

    color_correction_switch = ctk.CTkSwitch(root, text=lm.UI_LABEL_COLOR_CORRECTION, command=lambda: setattr(modules.globals, 'color_correction', color_correction_switch.get()))
    color_correction_switch.grid(row=4, column=2, padx=10, pady=5, sticky='w')
    update_ui_elements_text()
    
    
def select_source_path() -> None:
    global PREVIEW, RECENT_DIRECTORY_SOURCE

    if PREVIEW:
        PREVIEW.withdraw()

    if modules.globals.use_source_folder:
        folder_path = ctk.filedialog.askdirectory(title=lm.UI_SELECT_DIALOG_SOURCE_FOLDER, initialdir=RECENT_DIRECTORY_SOURCE)
        if folder_path:
            modules.globals.source_folder_path = folder_path
            RECENT_DIRECTORY_SOURCE = folder_path
    else:
        file_path = ctk.filedialog.askopenfilename(filetypes=[modules.globals.file_types[0]], title=lm. UI_SELECT_DIALOG_IMAGE, initialdir=RECENT_DIRECTORY_SOURCE)
        if file_path:
            modules.globals.source_path = file_path
            RECENT_DIRECTORY_SOURCE = os.path.dirname(file_path)
            update_image_preview(source_label, file_path)

def select_target_path() -> None:
    global RECENT_DIRECTORY_TARGET

    if PREVIEW:
        PREVIEW.withdraw()

    if modules.globals.use_target_folder:
        folder_path = ctk.filedialog.askdirectory(title=lm.UI_SELECT_DIALOG_TARGET_FOLDER, initialdir=RECENT_DIRECTORY_TARGET)
        if folder_path:
            modules.globals.target_folder_path = folder_path
            RECENT_DIRECTORY_TARGET = folder_path
    else:
        file_path = ctk.filedialog.askopenfilename(filetypes=modules.globals.file_types, title=lm.UI_SELECT_DIALOG_TARGET_FILE, initialdir=RECENT_DIRECTORY_TARGET)
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
        return ctk.filedialog.askdirectory(title=lm.UI_SELECT_DIALOG_OUTPUT_FOLDER, initialdir=RECENT_DIRECTORY_SOURCE)
    
    valid = False
    file_path = None
    if is_image(modules.globals.target_path):
        file_path = ctk.filedialog.asksaveasfilename(filetypes=[modules.globals.file_types[0]], title=lm. UI_SELECT_DIALOG_OUTPUT_FILE, initialdir=RECENT_DIRECTORY_OUTPUT)
        valid = True
    if is_video(modules.globals.target_path):
        file_path = ctk.filedialog.asksaveasfilename(filetypes=[modules.globals.file_types[1]], title=lm. UI_SELECT_DIALOG_OUTPUT_FILE, initialdir=RECENT_DIRECTORY_OUTPUT)
        valid = True
    
    if not valid:
        update_status("Error: No valid input target defined")
    
    return file_path

    
def update_ui_elements_text() -> None:
    global lm
    lm = language_manager.get_language()

    # Toggle first, update status label after
    toggle_source_mode(modules.globals.use_source_folder)
    toggle_target_mode(modules.globals.use_target_folder)
    
    status_label.configure(text=lm.UI_STATUS_TEXT_WELCOME_MESSAGE)
    donate_label.configure(text=lm.UI_BUTTON_DONATE)

    start_button.configure(text=lm.UI_BUTTON_START_PROCESS)
    stop_button.configure(text=lm.UI_BUTTON_STOP_PROCESS)
    preview_button.configure(text=lm.UI_BUTTON_PREVIEW)
    live_button.configure(text=lm.UI_BUTTON_LIVE)
    change_language_button.configure(text=lm.UI_BUTTON_LANGUAGE)

    use_folder_as_source_switch.configure(text=lm.UI_LABEL_USE_FOLDER_AS_SOURCE)
    use_folder_as_target_switch.configure(text=lm.UI_LABEL_USE_FOLDER_AS_TARGET)
    keep_frames_switch.configure(text=lm.UI_LABEL_KEEP_FRAMES)
    enhancer_switch.configure(text=lm.UI_LABEL_FACE_ENHANCER)
    keep_audio_switch.configure(text=lm.UI_LABEL_KEEP_AUDIO)
    many_faces_switch.configure(text=lm.UI_LABEL_MANY_FACES)
    color_correction_switch.configure(text=lm.UI_LABEL_COLOR_CORRECTION)
    keep_fps_checkbox.configure(text=lm.UI_LABEL_KEEP_FPS)

def toggle_source_mode(use_folder: bool) -> None:
    modules.globals.use_source_folder = use_folder
    if use_folder:
        select_face_button.configure(text=lm.UI_BUTTON_SELECT)
        source_label.configure(text=lm.UI_LABEL_SOURCE_FOLDER_TEXT)
        status_label.configure(text=lm.UI_STATUS_TEXT_FOLDER_AS_SOURCE_ACTIVE)
    else:
        select_face_button.configure(text=lm.UI_BUTTON_SELECT)
        source_label.configure(text=lm.UI_LABEL_SOURCE_FILE_TEXT)
        status_label.configure(text=lm.UI_STATUS_TEXT_FOLDER_AS_SOURCE_INACTIVE)
 
def toggle_target_mode(use_folder: bool) -> None:
    modules.globals.use_target_folder = use_folder
    if use_folder:
        select_target_button.configure(text=lm.UI_BUTTON_SELECT)
        target_label.configure(text=lm.UI_LABEL_TARGET_FOLDER_TEXT)
        status_label.configure(text=lm.UI_STATUS_TEXT_FOLDER_AS_TARGET_ACTIVE)
    else:
        select_target_button.configure(text=lm.UI_BUTTON_SELECT)
        target_label.configure(text=lm.UI_LABEL_TARGET_FILE_TEXT)
        status_label.configure(text=lm.UI_STATUS_TEXT_FOLDER_AS_TARGET_INACTIVE)