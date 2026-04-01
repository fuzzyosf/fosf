#!/usr/bin/env python3

import os
import pathlib

FOSF_ROOT = os.path.join(pathlib.Path.home(), ".fosf")
DATA_DIR = os.path.join(FOSF_ROOT, "data")
PICS_DIR = os.path.join(DATA_DIR, "pics")

SOURCE_DIR = os.path.realpath(os.path.dirname(__file__))
PROJECT_DIR = os.path.dirname(SOURCE_DIR)
TEST_DIR = os.path.join(PROJECT_DIR, "tests")
