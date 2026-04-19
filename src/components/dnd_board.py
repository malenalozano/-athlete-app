"""
src/components/dnd_board.py

declare_component must be called from an imported module (not an exec'd page
script) so that inspect.getmodule() can resolve the caller frame correctly.
"""
import os
import streamlit.components.v1 as _stc

_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dnd_board_static")

# Declared once at import time — safe to import from any page
dnd_board = _stc.declare_component("dnd_board", path=_STATIC_DIR)
