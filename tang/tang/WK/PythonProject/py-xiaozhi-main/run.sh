#!/bin/bash
unset CYCLONEDDS_HOME
export CYCLONEDDS_HOME=/home/unitree/tang/cyclonedds/install
export LD_LIBRARY_PATH=/home/unitree/tang/cyclonedds/install/lib
python3.9 main.py

sudo date -s "2026-04-24 18:30:00"