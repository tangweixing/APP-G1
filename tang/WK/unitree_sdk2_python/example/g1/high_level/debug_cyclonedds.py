import sys
import os

print("Python version:", sys.version)
print("\nsys.path:")
for path in sys.path:
    print(f"  {path}")

print("\nLooking for cyclonedds module:")
for path in sys.path:
    cyclonedds_path = os.path.join(path, "cyclonedds")
    if os.path.exists(cyclonedds_path):
        print(f"  Found cyclonedds at: {cyclonedds_path}")
        print(f"  Contents: {os.listdir(cyclonedds_path)}")
        if "_clayer" in os.listdir(cyclonedds_path):
            print("  Found _clayer module!")
        else:
            print("  _clayer module not found!")
