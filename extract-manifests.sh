#!/bin/bash

# Use c2patool to get any C2PA manifest data associated with asset files
# Note: c2patool must be installed and in the PATH
# First argument is name of asset file, second argument is name of output directory
function extract_manifest() {
    if [ -f "$1" ]; then
        filename=$(basename -- "$1")
        basefilename="${filename%.*}"

        output_dir="$2/manifests/$basefilename"
        echo "Running command: c2patool -d $1 -o $output_dir -f"
        c2patool -d $1 -o $output_dir -f 
    fi
}

# Iterate through directories containing asset files and call extract_manfiest 
for dir in "video/mp4" "image/jpeg" "pdf"; do
    for file in $PWD/$dir/*; do
        echo "Looking in directory $dir"
        extract_manifest "$file" "$dir"
    done
done
