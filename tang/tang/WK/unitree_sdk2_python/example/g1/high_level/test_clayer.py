import sys
sys.path.insert(0, '/usr/local/lib/python3.8/dist-packages/')
print("sys.path:", sys.path)
try:
    import cyclonedds._clayer
    print("Successfully imported cyclonedds._clayer")
    print("Module:", cyclonedds._clayer)
except Exception as e:
    print(f"Error importing cyclonedds._clayer: {e}")
    import traceback
    traceback.print_exc()
