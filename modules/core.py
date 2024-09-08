import os
import sys
# single thread doubles cuda performance - needs to be set before torch import
if any(arg.startswith('--execution-provider') for arg in sys.argv):
    os.environ['OMP_NUM_THREADS'] = '1'
# reduce tensorflow log level
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import warnings
from typing import List
import platform
import signal
import shutil
import argparse
import torch
import onnxruntime
import tensorflow

import modules.globals
import modules.metadata
import modules.ui as ui
from modules.processors.frame.core import get_frame_processors_modules
from modules.utilities import has_video_extension, has_image_extension, is_image, is_video, detect_fps, create_video, extract_frames, get_temp_frame_paths, restore_audio, create_temp, move_temp, clean_temp, normalize_output_path

if 'ROCMExecutionProvider' in modules.globals.execution_providers:
    del torch

warnings.filterwarnings('ignore', category=FutureWarning, module='insightface')
warnings.filterwarnings('ignore', category=UserWarning, module='torchvision')


def parse_args() -> None:
    signal.signal(signal.SIGINT, lambda signal_number, frame: destroy())
    program = argparse.ArgumentParser()
    program.add_argument('-sf', '--source_folder', help='select an source folder of images', dest='source_folder_path')
    program.add_argument('-tf', '--targe_folder', help='select an target folder of images', dest='target_folder_path')
    program.add_argument('-s', '--source', help='select an source image', dest='source_path')
    program.add_argument('-t', '--target', help='select an target image or video', dest='target_path')
    program.add_argument('-o', '--output', help='select output file or directory', dest='output_path')
    program.add_argument('--frame-processor', help='pipeline of frame processors', dest='frame_processor', default=['face_swapper'], choices=['face_swapper', 'face_enhancer'], nargs='+')
    program.add_argument('--keep-fps', help='keep original fps', dest='keep_fps', action='store_true', default=False)
    program.add_argument('--keep-audio', help='keep original audio', dest='keep_audio', action='store_true', default=True)
    program.add_argument('--keep-frames', help='keep temporary frames', dest='keep_frames', action='store_true', default=False)
    program.add_argument('--many-faces', help='process every face', dest='many_faces', action='store_true', default=False)
    program.add_argument('--nsfw-filter', help='filter the NSFW image or video', dest='nsfw_filter', action='store_true', default=False)
    program.add_argument('--video-encoder', help='adjust output video encoder', dest='video_encoder', default='libx264', choices=['libx264', 'libx265', 'libvpx-vp9'])
    program.add_argument('--video-quality', help='adjust output video quality', dest='video_quality', type=int, default=18, choices=range(52), metavar='[0-51]')
    program.add_argument('--live-mirror', help='The live camera display as you see it in the front-facing camera frame', dest='live_mirror', action='store_true', default=False)
    program.add_argument('--live-resizable', help='The live camera frame is resizable', dest='live_resizable', action='store_true', default=False)
    program.add_argument('--max-memory', help='maximum amount of RAM in GB', dest='max_memory', type=int, default=suggest_max_memory())
    program.add_argument('--execution-provider', help='execution provider', dest='execution_provider', default=['cpu'], choices=suggest_execution_providers(), nargs='+')
    program.add_argument('--execution-threads', help='number of execution threads', dest='execution_threads', type=int, default=suggest_execution_threads())
    program.add_argument('-v', '--version', action='version', version=f'{modules.metadata.name} {modules.metadata.version}')

    # register deprecated args
    program.add_argument('-f', '--face', help=argparse.SUPPRESS, dest='source_path_deprecated')
    program.add_argument('--cpu-cores', help=argparse.SUPPRESS, dest='cpu_cores_deprecated', type=int)
    program.add_argument('--gpu-vendor', help=argparse.SUPPRESS, dest='gpu_vendor_deprecated')
    program.add_argument('--gpu-threads', help=argparse.SUPPRESS, dest='gpu_threads_deprecated', type=int)

    args = program.parse_args()

    modules.globals.source_path = args.source_path
    modules.globals.target_path = args.target_path
    modules.globals.source_folder_path = args.source_folder_path
    modules.globals.target_folder_path = args.target_folder_path
    modules.globals.output_path = normalize_output_path(modules.globals.source_path, modules.globals.target_path, args.output_path)
    modules.globals.frame_processors = args.frame_processor
    modules.globals.headless = args.source_path or args.target_path or args.output_path
    modules.globals.keep_fps = args.keep_fps
    modules.globals.keep_audio = args.keep_audio
    modules.globals.keep_frames = args.keep_frames
    modules.globals.many_faces = args.many_faces
    modules.globals.nsfw_filter = args.nsfw_filter
    modules.globals.video_encoder = args.video_encoder
    modules.globals.video_quality = args.video_quality
    modules.globals.live_mirror = args.live_mirror
    modules.globals.live_resizable = args.live_resizable
    modules.globals.max_memory = args.max_memory
    modules.globals.execution_providers = decode_execution_providers(args.execution_provider)
    modules.globals.execution_threads = args.execution_threads

    #for ENHANCER tumbler:
    if 'face_enhancer' in args.frame_processor:
        modules.globals.fp_ui['face_enhancer'] = True
    else:
        modules.globals.fp_ui['face_enhancer'] = False

    # translate deprecated args
    if args.source_path_deprecated:
        print('\033[33mArgument -f and --face are deprecated. Use -s and --source instead.\033[0m')
        modules.globals.source_path = args.source_path_deprecated
        modules.globals.output_path = normalize_output_path(args.source_path_deprecated, modules.globals.target_path, args.output_path)
    if args.cpu_cores_deprecated:
        print('\033[33mArgument --cpu-cores is deprecated. Use --execution-threads instead.\033[0m')
        modules.globals.execution_threads = args.cpu_cores_deprecated
    if args.gpu_vendor_deprecated == 'apple':
        print('\033[33mArgument --gpu-vendor apple is deprecated. Use --execution-provider coreml instead.\033[0m')
        modules.globals.execution_providers = decode_execution_providers(['coreml'])
    if args.gpu_vendor_deprecated == 'nvidia':
        print('\033[33mArgument --gpu-vendor nvidia is deprecated. Use --execution-provider cuda instead.\033[0m')
        modules.globals.execution_providers = decode_execution_providers(['cuda'])
    if args.gpu_vendor_deprecated == 'amd':
        print('\033[33mArgument --gpu-vendor amd is deprecated. Use --execution-provider cuda instead.\033[0m')
        modules.globals.execution_providers = decode_execution_providers(['rocm'])
    if args.gpu_threads_deprecated:
        print('\033[33mArgument --gpu-threads is deprecated. Use --execution-threads instead.\033[0m')
        modules.globals.execution_threads = args.gpu_threads_deprecated


def encode_execution_providers(execution_providers: List[str]) -> List[str]:
    return [execution_provider.replace('ExecutionProvider', '').lower() for execution_provider in execution_providers]


def decode_execution_providers(execution_providers: List[str]) -> List[str]:
    return [provider for provider, encoded_execution_provider in zip(onnxruntime.get_available_providers(), encode_execution_providers(onnxruntime.get_available_providers()))
            if any(execution_provider in encoded_execution_provider for execution_provider in execution_providers)]


def suggest_max_memory() -> int:
    if platform.system().lower() == 'darwin':
        return 4
    return 16


def suggest_execution_providers() -> List[str]:
    return encode_execution_providers(onnxruntime.get_available_providers())


def suggest_execution_threads() -> int:
    if 'DmlExecutionProvider' in modules.globals.execution_providers:
        return 1
    if 'ROCMExecutionProvider' in modules.globals.execution_providers:
        return 1
    return 8


def limit_resources() -> None:
    # prevent tensorflow memory leak
    gpus = tensorflow.config.experimental.list_physical_devices('GPU')
    for gpu in gpus:
        tensorflow.config.experimental.set_memory_growth(gpu, True)
    # limit memory usage
    if modules.globals.max_memory:
        memory = modules.globals.max_memory * 1024 ** 3
        if platform.system().lower() == 'darwin':
            memory = modules.globals.max_memory * 1024 ** 6
        if platform.system().lower() == 'windows':
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetProcessWorkingSetSize(-1, ctypes.c_size_t(memory), ctypes.c_size_t(memory))
        else:
            import resource
            resource.setrlimit(resource.RLIMIT_DATA, (memory, memory))


def release_resources() -> None:
    if 'CUDAExecutionProvider' in modules.globals.execution_providers:
        torch.cuda.empty_cache()


def pre_check() -> bool:
    if sys.version_info < (3, 9):
        update_status('Python version is not supported - please upgrade to 3.9 or higher.')
        return False
    if not shutil.which('ffmpeg'):
        update_status('ffmpeg is not installed.')
        return False
    return True


def update_status(message: str, scope: str = 'DLC.CORE') -> None:
    print(f'[{scope}] {message}')
    if not modules.globals.headless:
        ui.update_status(message)

def destroy(to_quit=True) -> None:
    if modules.globals.target_path:
        clean_temp(modules.globals.target_path)
    if to_quit: quit()


def run() -> None:
    parse_args()
    if not pre_check():
        return
    for frame_processor in get_frame_processors_modules(modules.globals.frame_processors):
        if not frame_processor.pre_check():
            return
    limit_resources()
    if modules.globals.headless:
        start()
    else:
        window = ui.init(start, destroy)
        window.mainloop()


def start() -> None:
    update_status('Processing...')
    
    if modules.globals.nsfw_filter and ui.check_and_ignore_nsfw(modules.globals.target_path, destroy):
        return
    for frame_processor in get_frame_processors_modules(modules.globals.frame_processors):
        target_files = []
        
        # Check what type of target frame we have
        if modules.globals.target_folder_path:
            target_files = next(os.walk(modules.globals.target_folder_path), (None, None, []))[2] 
        elif modules.globals.target_path: 
            if os.path.isfile:
                target_files.append(modules.globals.target_path)
            else:
                update_status('Error: Input target not a valid file or directory..')
                print('Error: Input target not a valid file or directory..')
                return 
        else:
            update_status('Error: No input target defined..')
            print('Error: No input target defined..')
            return  
        
        
        output_files = []
        
        
        # Process
        update_status('Progressing...', frame_processor.NAME)
        
        # Handle source file(s)
        source_files = []
        if modules.globals.source_folder_path:
            source_files = next(os.walk(modules.globals.source_folder_path), (None, None, []))[2]
        else:
            if modules.globals.source_path:
                source_files.append(modules.globals.source_path)
            else:
                update_status('Error: No input source defined..')
                print('Error: No input source defined..')
                return
        # Handle source file(s) 
        for source_file in source_files:
            if not ((has_image_extension(source_file) or has_video_extension(source_file))):
                continue
            # Create a dedicated output folder for each source frame
            if len(source_files) > 1:
                output_subfolder_name = None
                output_subfolder_path = None
                output_subfolder_name = os.path.splitext(source_file)[0]  # Use the frame name without extension as the folder name
                output_subfolder_path = os.path.join(modules.globals.output_path, output_subfolder_name)
                os.makedirs(output_subfolder_path, exist_ok=True)
            else:
                output_subfolder_path = None
            
            # Create files to modify
            update_status('Copying files...', frame_processor.NAME)
            output_files = []  # Reset output frames for each source frame
            for target_file in target_files:
                if modules.globals.target_folder_path:
                    target_file_path = os.path.join(modules.globals.target_folder_path, target_file)
                elif modules.globals.target_path:
                    target_file_path = modules.globals.target_path
                if (has_image_extension(source_file) or has_video_extension(source_file)) and (has_image_extension(target_file_path) or has_video_extension(target_file_path)):
                    output_file_name = f"{os.path.splitext(source_file)[0]}_{os.path.basename(target_file_path)}"
                    if output_subfolder_path:
                        output_file_path = os.path.join(output_subfolder_path, output_file_name)
                    else:
                        output_file_path = modules.globals.output_path # os.path.join(output_subfolder_path, output_file_name)
                    try:
                        if modules.globals.target_folder_path:
                            pwd = os.path.join(modules.globals.target_folder_path, target_file)
                        else:
                            pwd = modules.globals.target_path
                        shutil.copy(pwd, output_file_path)
                    except Exception as e:
                        print(f"Error copying file {target_file}: {e}")
                    output_files.append(output_file_path)
            
            # Process
            if modules.globals.source_folder_path:
                modules.globals.source_path = f"{modules.globals.source_folder_path}/{source_file}"
            else:
                modules.globals.source_path = f"{source_file}"
               
            print(modules.globals.source_path)
            for frame_processor in get_frame_processors_modules(modules.globals.frame_processors):
                if not frame_processor.pre_start():
                    return
                # process image to image
            for target_file in output_files:
                modules.globals.target_path = target_file
                modules.globals.output_path = target_file
                if has_image_extension(modules.globals.target_path):
                    if modules.globals.nsfw_filter and ui.check_and_ignore_nsfw(modules.globals.target_path, destroy):
                        return
                    for frame_processor in get_frame_processors_modules(modules.globals.frame_processors):
                        update_status('Progressing...', frame_processor.NAME)
                        print('Progressing...', frame_processor.NAME)
                        frame_processor.process_target_folder(modules.globals.source_path, output_files)
                        # frame_processor.process_image(modules.globals.source_path, modules.globals.output_path, modules.globals.output_path)
                        release_resources()
                    if is_image(modules.globals.target_path):
                        update_status('Processing to image succeed!')
                    else:
                        update_status('Processing to image failed!')
                    continue
                # process image to videos
                if modules.globals.nsfw_filter and ui.check_and_ignore_nsfw(modules.globals.target_path, destroy):
                    return
               
                update_status('Creating temp resources...')
                create_temp(modules.globals.target_path)
                update_status('Extracting frames...')
                extract_frames(modules.globals.target_path)
                temp_frame_paths = get_temp_frame_paths(modules.globals.target_path)
                for frame_processor in get_frame_processors_modules(modules.globals.frame_processors):
                    update_status('Progressing...', frame_processor.NAME)
                    frame_processor.process_video(modules.globals.source_path, temp_frame_paths)
                    release_resources()
                # handles fps
                if modules.globals.keep_fps:
                    update_status('Detecting fps...')
                    fps = detect_fps(modules.globals.target_path)
                    update_status(f'Creating video with {fps} fps...')
                    create_video(modules.globals.target_path, fps)
                else:
                    update_status('Creating video with 30.0 fps...')
                    create_video(modules.globals.target_path)
                # handle audio
                if modules.globals.keep_audio:
                    if modules.globals.keep_fps:
                        update_status('Restoring audio...')
                    else:
                        update_status('Restoring audio might cause issues as fps are not kept...')
                    restore_audio(modules.globals.target_path, modules.globals.output_path)
                else:
                    move_temp(modules.globals.target_path, modules.globals.output_path)
                # clean and validate
                clean_temp(modules.globals.target_path)
                if is_video(modules.globals.target_path):
                    update_status('Processing to video succeed!')
                else:
                    update_status('Processing to video failed!')
        