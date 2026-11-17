#!/usr/bin/env python3
"""Launch BatiPlan Studio."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from batiplan.gui import main

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
