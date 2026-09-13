"""Import this before using pcbnew iteration APIs.

KiCad 10.0.6 ships a pcbnew.py whose container __iter__ methods call
`it.next()` -- a Python-2 idiom. This SWIG build exposes only `__next__`, so
Board.GetTracks(), GetDrawings(), GetFootprints() and friends raise
AttributeError on Python 3.14. The bug is in KiCad's bindings, not in
anything we or kbplacer wrote.

    import kicad_compat  # noqa: F401
    import pcbnew
"""
import pcbnew

if not hasattr(pcbnew.SwigPyIterator, "next"):
    pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__
