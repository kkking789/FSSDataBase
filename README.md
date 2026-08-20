[README.md](https://github.com/user-attachments/files/31246465/README.md)
# FSSDataBase

FSSDataBase is a Python workflow for generating, simulating, storing, and
reconstructing frequency-selective-surface (FSS) unit-cell samples.  It uses
Ansys HFSS through PyAEDT to construct multilayer periodic structures, run
modal simulations, extract reflection and transmission responses, and write
sample-level artifacts together with a compact SQLite index.

> This repository drives licensed Ansys Electronics Desktop/HFSS software. It
> is not a stand-alone electromagnetic solver.

## Features

- Random or prescribed multilayer dielectric/metal stack-ups.
- Three internal metal-geometry generators (`group1`, `group2`, and `group3`).
- Floquet-port excitation and master/slave periodic boundaries for unit-cell
  simulations.
- Frequency and incidence-angle sweeps configured in `settings.yaml`.
- Per-sample raw S-parameter magnitude/phase files, label files, reconstruction
  metadata, structure images, and binary masks.
- SQLite storage of fixed-length response and phase vectors.
- Reconstruction of an HFSS model from a sample's `data.json` file.

## Repository layout

```text
.
├── DataBaseLocal.py          # Main data-generation entry point
├── settings.yaml             # Generation and simulation configuration
├── requirements.txt          # Python dependencies excluding PyAEDT
├── JsonDetail                # Brief description of reconstruction metadata
└── utils/
    ├── tools.py              # HFSS modelling, simulation, and file generation
    ├── DataBase.py           # SQLite schema and insert operations
    ├── CacheGenerate.py      # Fixed-grid cache and response-vector handling
    ├── rebuild.py            # Reconstructs an HFSS model from data.json
    ├── types.py              # Configuration data classes
    └── BasicGenerate/        # FSS geometry generators
```

## Prerequisites

Before running the generator, install and configure:

1. A licensed installation of Ansys Electronics Desktop with HFSS.
2. An AEDT release matching `AEDT_VERSION` in `settings.yaml` (the bundled
   example uses `2023.1`).
3. Python and an environment able to launch PyAEDT and AEDT on the local
   machine.
4. PyAEDT `0.25.1`.

Install the Python dependencies from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Configure a run

Edit `settings.yaml` before starting a generation run. In particular, replace
the example Windows paths under `path` and `database` with writable absolute
paths on your machine.

| Setting | Meaning |
|---|---|
| `AEDT_VERSION` | AEDT/HFSS version passed to PyAEDT. |
| `NUM_CORES` | Number of CPU cores requested for each HFSS solve. |
| `path` | Root directory for per-sample artifacts and cache files. |
| `database` | Directory in which `DataBase.db` is created. |
| `samples` | Number of generation attempts. Start with `1` for a smoke test. |
| `storage_points` | Number of fixed-grid values stored per database response vector. |
| `unit.size` | Generator size parameter in mm. The current model builder uses a lateral periodic dimension of `2 × unit.size`. |
| `unit.wire_width` | Metal-line width in mm. A scalar is fixed; a two-value list is sampled uniformly. |
| `materials` | Named dielectric-material definitions. |
| `stackup` | Selects either `random` or `arrangement` layer construction. |
| `frequency` | List of `[start_GHz, stop_GHz, requested_points]` sweep definitions. |
| `angle` | Optional list of `[start_deg, stop_deg, step_deg]` incidence-angle sweeps. |

### Stack-up modes

- `random`: randomly chooses the configured numbers of dielectric and metal
  layers, candidate dielectric materials, dielectric thicknesses, and metal
  geometry groups.
- `arrangement`: builds the explicitly listed layer sequence. Check that each
  material name in this section also appears in `materials`.

The example configuration is intended as a starting point. Review all material
names, dimensions, frequency ranges, angular sweeps, layer counts, and compute
resource settings before a production run.

## Run data generation

From the repository root, run:

```powershell
python DataBaseLocal.py
```

The script creates a dedicated Python process for each generation attempt and
starts HFSS in non-graphical mode. A sample is retained only when structure
creation and simulation complete successfully; failed sample directories are
removed by the workflow.

Generation can be computationally expensive. Confirm the AEDT license,
configured paths, and a one-sample smoke test before increasing `samples` or
`NUM_CORES`.

## Generated data

Each successful sample is stored in a directory named with its timestamp-derived
identifier. The identifier is the number of elapsed seconds since
00:00:00 UTC on 1 January 1970.

### Per-sample artifacts

| File or pattern | Description |
|---|---|
| `raw_result.csv` | Headerless, comma-delimited raw response matrix. Columns are angle, frequency, TE/TM S11 magnitude, TE/TM S21 magnitude, and their phases. Magnitudes are in dB; phases are in degrees. |
| `label_result.csv` | Headerless, comma-delimited label matrix. The current code labels each S-parameter magnitude as `1` when it is greater than the default threshold of `-5 dB`, otherwise `-1`; phase columns are retained. |
| `data.json` | Metadata and build operations used for reconstruction. |
| `structure_<idx>.png` | Grayscale visualisation of one generated metal structure. |
| `mask_<idx>.csv` | Headerless comma-delimited binary mask corresponding to `structure_<idx>.png`. The default resolution is 500 × 500. |
| `<start>~<stop>Ghz_<component>.png` | Response visualisation. Components include `S11TE`, `S11TM`, `S21TE`, `S21TM`, and their `_angle` phase variants. |

The number of `structure_<idx>.png` and `mask_<idx>.csv` pairs is
sample-dependent. Their indices start at zero.

### Raw-response column order

`raw_result.csv` contains the following ten columns, without a header:

```text
angle,
frequency,
S11_TE_dB,
S11_TM_dB,
S21_TE_dB,
S21_TM_dB,
S11_TE_phase_deg,
S11_TM_phase_deg,
S21_TE_phase_deg,
S21_TM_phase_deg
```

`label_result.csv` keeps the same first two and final four phase columns. Its
four magnitude columns contain the corresponding binary labels.

### SQLite database

The workflow creates `DataBase.db` using SQLite. It contains:

| Table | Purpose |
|---|---|
| `samples` | Parent table containing `id`, `sample_path`, `size`, and `height`. |
| `responses` | Child table containing integer response vectors for each `(id, direct, angle)` tuple. `direct=0` denotes S11 and `direct=1` denotes S21. |
| `responses_angle` | Child table containing floating-point phase vectors for the same `(id, direct, angle)` tuple. |

Both child tables have vector columns `p000` through `p[N-1]`, where `N` is
`storage_points`. The database vectors are fixed-grid representations produced
by the cache stage; use `raw_result.csv` when the original continuous response
samples are required.

## Rebuild a sample

`utils.rebuild.Rebuild` reads `data.json`, reconstructs the recorded geometry,
registers materials, recreates substrates and boundaries, and configures the
stored frequency and angle sweeps. It builds a new HFSS project; it does not
run the solve automatically.

```python
from utils.rebuild import Rebuild

rebuild = Rebuild(
    data_path=r"C:\\path\\to\\sample\\data.json",
    project_path=r"C:\\path\\to\\rebuild_output",
    idx=0,
    AEDT_VERSION="2023.1",
)
rebuild.rebuild()
```

Run this code from the repository root, with the same AEDT/PyAEDT environment
used for generation.

## Troubleshooting

| Symptom | Suggested check |
|---|---|
| AEDT or PyAEDT cannot start | Confirm the AEDT installation, license availability, and that `AEDT_VERSION` matches the installed release. |
| No output directory is retained | Inspect the console trace; invalid geometry or a failed HFSS solve causes the sample directory to be removed. |
| Path-related errors | Use writable absolute paths for `path` and `database`; avoid the bundled example paths. |
| Material lookup error | Ensure every material referenced by `stackup` is defined in `materials`. |
| Reconstruction fails | Use the same AEDT version where possible and confirm that `data.json` has not been modified. |
