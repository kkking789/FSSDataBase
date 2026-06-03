import os
import re

import numpy as np



class CacheOperate:
    def __init__(self, path: str, batch_size: int = 100, start: int = 1, stop: int = 30, points: int = 300):
        self.path = path+r"\cache"
        self.batch_size = batch_size
        self.start = start
        self.stop = stop
        self.points = points

        os.makedirs(self.path, exist_ok=True)
        self.ids = []
        self.angles = []
        self.directs = [] # 0 means S11,1 means S21
        self.Sparameters = []
        self.idx = 0
        self.freq = np.linspace(start, stop, points, dtype=np.float32)
        self.batch_idx = self._next_batch_idx()

    def read(self):
        ids = []
        angles = []
        sparameters = []
        directs = []

        for filename in sorted(os.listdir(self.path)):
            if not filename.endswith(".npz"):
                continue

            data = np.load(os.path.join(self.path, filename), allow_pickle=False)

            ids.append(data["ids"])
            angles.append(data["angles"])
            sparameters.append(data["Sparameters"])
            directs.append(data["directs"])

        if not ids:
            return (
                np.asarray([], dtype=np.int64),
                np.asarray([], dtype=np.int8),
                np.asarray([], dtype=np.float32),
                np.asarray([], dtype=np.float32),
            )

        return (
            np.concatenate(ids, axis=0),
            np.concatenate(directs, axis=0),
            np.concatenate(angles, axis=0),
            np.concatenate(sparameters, axis=0),
        )

    def write(self, ids: int, direct: int, angle: float, Sparameters: list, freqs: list):
        data = self._normalize(Sparameters, freqs)
        self.idx += 1
        self.angles.append(angle)
        self.Sparameters.append(data)
        self.ids.append(ids)
        self.directs.append(direct)

        if self.idx%self.batch_size == 0:
            self.flush()

    def flush(self):
        np.savez(
            os.path.join(self.path, f"cache_{self.batch_idx:05}.npz"),
            ids=self.ids,
            directs=self.directs,
            angles=self.angles,
            Sparameters=self.Sparameters,
        )

        self.batch_idx += 1
        self.ids.clear()
        self.directs.clear()
        self.angles.clear()
        self.Sparameters.clear()

    def _next_batch_idx(self) -> int:
        pattern = re.compile(r"cache_(\d+)\.npz$")

        max_idx = -1
        for filename in os.listdir(self.path):
            match = pattern.match(filename)
            if match:
                max_idx = max(max_idx, int(match.group(1)))

        return max_idx + 1

    def _normalize(self, Sparameters: list, freqs:list):
        freqs = np.array(freqs)
        Sparameters = np.array(Sparameters)

        target_freq = self.freq
        output = np.full(self.points, -1, dtype=np.int8)

        for idx, freq in enumerate(target_freq):
            if freq < freqs[0] or freq > freqs[-1]:
                continue
            ids = np.searchsorted(freqs, freq)
            ids = min(ids, len(Sparameters) - 1)
            output[idx] = Sparameters[ids]
        return output
