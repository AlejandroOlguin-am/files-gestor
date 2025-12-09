import os
import hashlib
import shutil

def delete_duplicate_files(directory):
    """Delete duplicate files in the given directory."""
    file_hashes = {}
    duplicates = []

    for root, _, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            file_hash = hash_file(filepath)

            if file_hash in file_hashes:
                duplicates.append(filepath)
            else:
                file_hashes[file_hash] = filepath

    for duplicate in duplicates:
        os.remove(duplicate)
        print(f"Deleted duplicate file: {duplicate}")