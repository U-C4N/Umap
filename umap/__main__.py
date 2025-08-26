"""Allows Umap to be run as a module using 'python -m umap'."""

if __name__ == "__main__":
    import sys
    import os
    
    # Add parent directory to path for module imports
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    try:
        from umap.cli import main
    except ImportError:
        # Fallback for direct execution
        sys.path.insert(0, os.path.dirname(__file__))
        from cli import main
    
    main()