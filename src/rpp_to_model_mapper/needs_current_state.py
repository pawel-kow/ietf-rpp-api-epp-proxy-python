class NeedsCurrentState(Exception):
    """The patch operation cannot become an EPP update without the current object (#27)."""
