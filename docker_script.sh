#!/bin/bash

target_ext="jpg" # [jpg, png, mp4 ...]
source_ext="jpg"
# Define paths
source_dir="output/source_files" 
target_dir="output/target_files"
output_dir="output/output_files"
enhanced_folder="output/enhanced"
# Ensure output directory exists
mkdir -p "${output_dir}"
mkdir -p "${enhanced_folder}"

# Function to generate a unique filename
generate_unique_filename() {
    local base_name=$1
    local output_dir=$2
    local output_file="${output_dir}/${base_name}"
    local counter=1

    while [ -e "${output_file}" ]; do
        output_file="${output_dir}/${base_name%.*}_$counter.${base_name##*.}"
        counter=$((counter + 1))
    done

    echo "${output_file}"
}

# Function to process files
process_files() {

    local target_ext=$1
    local source_ext=$2
    local in_dir=$3
    local run_face_enhance=$4 

    for target_file in "${target_dir}"/*.${target_ext}; do
        if [ ! -e "${target_file}" ]; then
            echo "No target files with extension ${target_ext} found in ${target_dir}"
            continue
        fi

        
        base_name=$(basename "${target_file}")
        for input_file in "${source_dir}"/*.${source_ext}; do
            if [ ! -e "${source_dir}" ]; then
                echo "No input files found in ${source_dir}"
                continue
            fi

            # Generate a unique output file name

            input_base_name=$(basename "${input_file}")

            name=$(echo "$input_base_name" | sed "s/.$source_ext/_/g")${base_name}
            # Generate a unique output file name
            output_file=$(generate_unique_filename "${name}" "${output_dir}")
            
            # Run Docker Compose with overridden command
                python3 run.py \
                -s "${input_file}" \
                -t "${target_file}" \
                -o "${output_file}" \
                --execution-provider cuda \
                --frame-processor face_swapper \
                --many-faces \
                --execution-threads 4 \
                --video-encoder libx265 \
                --video-quality 0 \
                --keep-fps \
                --keep-audio \
                --max-memory 8

            echo "Saved to ${output_file}"
                    python3 run.py \
                    -s "${input_file}" \
                    -t "${output_file}" \
                    -o $(generate_unique_filename "${name}" "${enhanced_folder}") \
                    --execution-provider cuda \
                    --frame-processor "face_enhancer" \
                    --execution-threads 4 \
                    --video-encoder libx265 \
                    --video-quality 0 \
                    --keep-fps \
                    --keep-frames \
                    --keep-audio \
                    --max-memory 8

        done
    done
}
# Function to process files
enhance_files() {
    local target_ext=$1
    local source_ext=$2
    local target_dir=$3
    local source_dir=$4
    local output_dir=$5
    echo "No target files with extension ${target_ext} found in ${target_dir}"
    local frame_processor=$6
    for target_file in "${target_dir}"/*.${target_ext}; do
        if [ ! -e "${target_file}" ]; then
            echo "No target files with extension ${target_ext} found in ${target_dir}"
            continue
        fi
        target_base_name=$(basename "${target_file}")
        

        for input_file in "${source_dir}"/*.${source_ext}; do
            if [ ! -e "${source_dir}" ]; then
                echo "No input files found in ${source_dir}"
                continue
            fi
            input_base_name=$(basename "${input_file}")
            substr=$(echo "$input_base_name" | sed "s/.$source_ext//g")
            
            if [[ $target_file == *"$substr"* ]]; then
               
                name=$(echo "$input_base_name" | sed "s/.$source_ext/_enhanced.${target_ext}/g")
                # Generate a unique output file name
                output_file=$(generate_unique_filename "${name}" "${output_dir}")
                # Run Docker Compose with overridden command
                echo $output_file
                docker compose run --rm  webdeep \
                    -s "${input_file}" \
                    -t "${target_file}" \
                    -o "${output_file}" \
                    --execution-provider cuda \
                    --frame-processor "face_enhancer" \
                    --execution-threads 4 \
                    --video-encoder libx265 \
                    --video-quality 0 \
                    --keep-fps \
                    --keep-frames \
                    --keep-audio \
                    --max-memory 6


                echo "Saved to ${output_file}"
            fi
        done
    done
}


process_files "${target_ext}" "${source_ext}" "${source_dir}" true
