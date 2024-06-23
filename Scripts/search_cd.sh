#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 <folder_name>"
    exit 1
fi

folder_name=$1

# Find directories matching the folder name
matches=$(find . -type d -name "*$folder_name*" -print 2>/dev/null)

if [ -z "$matches" ]; then
    echo "No matching directories found."
    exit 1
fi

echo "Select a directory to cd into:"
select dir in $matches; do
    if [ -n "$dir" ]; then
        cd "$dir" && echo "Changed directory to $(pwd)"
        break
    else
        echo "Invalid selection."
    fi
done

