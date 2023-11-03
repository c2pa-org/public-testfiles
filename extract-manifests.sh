#!/bin/bash

# Create YAML file listing all assets
dir="$PWD/image/jpeg"
output_file="_data/assets.yml"
echo "asset_files:" > "$output_file"

# Loop through all files in the directory and its subdirectories
find "$dir" -type f -print0 | while read -d $'\0' file; do
    echo "  - $(basename "$file")" >> "$output_file"
done

# Argument is name of asset file
function extract_manifest() {
    if [ -f "$1" ]; then

        filename=$(basename -- "$1")
        basefilename="${filename%.*}"
        output_dir="$PWD/manifests/image/jpeg/$basefilename"

        echo "Running c2patool on: $basefilename"
        c2patool $1 -o $output_dir -f

        echo "Running c2patool -d on: $basefilename"
        output_dir="$PWD/detailed-manifests/image/jpeg/$basefilename"
        c2patool $1 -o $output_dir -f
    fi
}

# Use c2patool to get any C2PA manifest data associated with images in /image/jpeg dir

for file in $PWD/image/jpeg/*; do
    extract_manifest "$file"
done

for file in $PWD/video/mp4/*; do
    extract_manifest "$file"
done

