"""Measure matching memory with many colors sharing the same candidates."""

import sys
import tracemalloc
from pathlib import Path
from time import perf_counter

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.montage_service import ElementRecord, match_elements


def main():
    # 4,096 unique colors, each matching all 4,096 materials.
    colors = np.indices((16, 16, 16)).reshape(3, -1).T.astype(np.uint8) + 120
    colors = colors.reshape(64, 64, 3)
    record = ElementRecord("unused", (0, 0, 1, 1), (128,) * 3, (128,) * 3)
    records = [record] * 4096
    tracemalloc.start()
    started = perf_counter()
    selected = match_elements(colors, records, "average", random_seed=17)
    elapsed = perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert selected.shape == (64, 64)
    assert np.all((selected >= 0) & (selected < len(records)))
    print(f"match: {elapsed * 1000:.2f} ms; peak tracked allocations: {peak / 1024**2:.2f} MiB")


if __name__ == "__main__":
    main()
