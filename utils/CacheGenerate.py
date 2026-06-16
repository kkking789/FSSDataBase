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
        self.Phase = []
        self.idx = 0
        self.freq = np.linspace(start, stop, points, dtype=np.float32)
        self.batch_idx = self._next_batch_idx()

    def read(self):
        ids = []
        angles = []
        sparameters = []
        directs = []
        phase = []

        for filename in sorted(os.listdir(self.path)):
            if not filename.endswith(".npz"):
                continue

            data = np.load(os.path.join(self.path, filename), allow_pickle=False)

            ids.append(data["ids"])
            angles.append(data["angles"])
            sparameters.append(data["Sparameters"])
            directs.append(data["directs"])
            if "phase" in data.files:
                phase.append(data["phase"])
            else:
                phase.append(np.full(data["Sparameters"].shape, np.nan, dtype=np.float16))

        if not ids:
            return (
                np.asarray([], dtype=np.int64),
                np.asarray([], dtype=np.int8),
                np.asarray([], dtype=np.float32),
                np.empty((0, self.points), dtype=np.int8),
                np.empty((0, self.points), dtype=np.float16),
            )

        return (
            np.concatenate(ids, axis=0),
            np.concatenate(directs, axis=0),
            np.concatenate(angles, axis=0),
            np.concatenate(sparameters, axis=0),
            np.concatenate(phase, axis=0),
        )

    def write(self, ids: int, direct: int, angle: float, Sparameters: list, Phase:list, freqs: list):
        data, phase = self._normalize(Sparameters, Phase, freqs)
        self.idx += 1
        self.angles.append(angle)
        self.Sparameters.append(data)
        self.Phase.append(phase)
        self.ids.append(ids)
        self.directs.append(direct)

        if self.idx%self.batch_size == 0:
            self.flush()
        return data, phase

    def flush(self):
        if not self.ids:
            return
        
        np.savez(
            os.path.join(self.path, f"cache_{self.batch_idx:05}.npz"),
            ids=self.ids,
            directs=self.directs,
            angles=self.angles,
            Sparameters=self.Sparameters,
            phase=self.Phase,
        )

        self.batch_idx += 1
        self.ids.clear()
        self.directs.clear()
        self.angles.clear()
        self.Sparameters.clear()
        self.Phase.clear()

    def _next_batch_idx(self) -> int:
        pattern = re.compile(r"cache_(\d+)\.npz$")

        max_idx = -1
        for filename in os.listdir(self.path):
            match = pattern.match(filename)
            if match:
                max_idx = max(max_idx, int(match.group(1)))

        return max_idx + 1

    def _normalize(self, Sparameters: list, Phase: list, freqs:list):
        freqs = np.array(freqs)
        Sparameters = np.array(Sparameters)
        Phase = np.array(Phase)

        target_freq = self.freq
        output = np.full(self.points, 0, dtype=np.int8)
        output_phase = np.full(self.points, np.nan, dtype=np.float16)

        for idx, freq in enumerate(target_freq):
            if freq < freqs[0] or freq > freqs[-1]:
                continue
            ids = np.searchsorted(freqs, freq, side="right")-1

            ids = min(ids, len(Sparameters) - 1)
            output[idx] = Sparameters[ids]

            ids = min(ids, len(Phase) - 1)
            output_phase[idx] = Phase[ids]

        return output, output_phase
