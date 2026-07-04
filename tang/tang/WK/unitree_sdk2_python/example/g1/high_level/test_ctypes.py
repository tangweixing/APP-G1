import ctypes
import os

# 直接使用 ctypes 加载 _clayer
clayer_path = '/usr/local/lib/python3.8/dist-packages/cyclonedds/_clayer.cpython-38-x86_64-linux-gnu.so'
try:
    lib = ctypes.CDLL(clayer_path)
    print(f"Successfully loaded {clayer_path}")
except Exception as e:
    print(f"Error loading {clayer_path}: {e}")
