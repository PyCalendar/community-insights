The image starts one gunicorn worker instead of two (``WORKERS=1``): each one needs about 300 MB, so the container fits into 600 MB. Set ``WORKERS=2`` for more at once.
