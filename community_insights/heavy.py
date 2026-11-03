"""The large libraries of the statistics and charts, loaded when first needed.

Pages served at the same time by several threads would otherwise load parts of them at the
same time, in another order, which Python's import stops as a deadlock: every lazy import of
them happens inside ``with LOCK:``.
"""

import threading

LOCK = threading.RLock()  # one thread at a time loads matplotlib, numpy, pandas, scipy, ...
