"""Allows Umap to be run as a module using 'python -m umap'."""

if __name__ == "__main__":
    # This is equivalent to running 'python umap/cli.py'
    # but allows 'python -m umap ...' to work without installation.
    from .cli import main
    main() 