import os

print("Current directory:", os.getcwd())
print("Upload folder path:", os.path.abspath('uploads'))
print("Exists?", os.path.exists('uploads'))
print("Writable?", os.access('uploads', os.W_OK))