import os
import sys

# Make the project root importable when pytest is run from any cwd.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
