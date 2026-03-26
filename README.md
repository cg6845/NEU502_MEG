# NEU502B — OPM-MEG Software Setup

Follow these four parts in order. Commands are ready to copy and paste.

---

## Contents

- [00 · Prerequisites](#00--prerequisites)
- [01 · Get the mne-opm software](#01--get-the-mne-opm-software)
- [02 · Download the sample data](#02--download-the-sample-data)
- [03 · Set up Jupyter notebooks](#03--set-up-jupyter-notebooks)
- [04 · Get the Oddball PsychoPy task](#04--get-the-oddball-psychopy-task)

---

## 00 · Prerequisites

### 🍎 Mac & Linux — Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

### 🪟 Windows users

> **Windows users are strongly encouraged to install WSL** (Windows Subsystem for Linux), which allows your machine to run Linux. Once WSL is set up, follow the Mac & Linux instructions above instead of the steps below.
>
> From **PowerShell (run as Administrator)**:
> ```powershell
> wsl --install
> ```
> This installs WSL 2 with Ubuntu by default. A reboot is required afterward.

The steps below only apply to Windows users **not** running WSL.

**1. Install uv**

From **PowerShell** (you may see a security prompt — this is expected and safe to proceed through):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**2. Install Git**

From **Windows Terminal**:

```powershell
winget install Git.Git
```

**3. Install Anaconda or Miniconda**

Download from [anaconda.com](https://www.anaconda.com) if you don't already have it, then open **Anaconda Prompt** and run:

```bash
conda install pyqt
conda install jupyterlab
```

---

## 01 · Get the mne-opm Software

**1. Clone the repository**

Navigate to your preferred software location first, then clone:

```bash
git clone -b my-working-branch https://github.com/mrribbits/mne-opm.git
```

**2. Enter the directory and sync dependencies**

```bash
cd mne-opm
uv sync
```

**3. Register the Jupyter kernel**

🪟 **Windows (not WSL)** — from the `mne-opm` directory, in **Anaconda Prompt**:

```bash
.venv\Scripts\activate
pip install ipykernel
python -m ipykernel install --user --name mne-opm --display-name "mne-opm"
```

🍎 **Mac or Linux (if you have kernel issues)** — from the `mne-opm` directory:

```bash
uv run python -m ipykernel install --user --name mne-opm --display-name "mne-opm"
```

---

## 02 · Download the Preprocessed Sample Data

**1. Navigate to your preferred data location and download**

```bash
curl -L -H "Cache-Control: no-cache" \
  -o "./MEG-for-students-preproc.zip" \
  "https://www.dropbox.com/scl/fi/mwk2xs6jcar5ppl6ahk0t/MEG-for-students-preproc.zip?rlkey=0bpthyvizakg1h8c9ncy10sp4&dl=1"
```

**2. Unzip the file**

```bash
unzip MEG-for-students-preproc.zip
```

---

## 03 · Set Up the Jupyter Notebooks

**1. Clone the course notebooks**

```bash
git clone https://github.com/mrribbits/NEU502-2026.git meg-notebooks
```

**2. Launch JupyterLab**

Point `uv` at your `mne-opm` install location:

```bash
uv run --project /path/to/your/mne-opm jupyter lab
```

> 💡 Once open, make sure the **mne-opm** kernel is selected. If it isn't chosen automatically, select it from the kernel menu in JupyterLab.

**3. Edit the path variables in each notebook**

Open each notebook and update the directory variables to match your local setup:

| Variable | Set in | Description | Example |
|---|---|---|---|
| `DERIV_DIR` | Notebooks 1–4 | Preprocessed derivatives folder | `~/classes/neu502/oddball/data/oddball/bids/derivatives/analysis1__/sub-001/ses-01/meg` |
| `RAW_DIR` | Notebook 1 | Raw BIDS data folder | `~/classes/neu502/oddball/data/oddball/bids/sub-001/ses-01/meg` |
| `SUBJECTS_DIR` | Notebook 3 | FreeSurfer subjects directory | `~/classes/neu502/oddball/data/oddball/bids/derivatives/freesurfer` |
| `PROJECT_ROOT` | Notebook 5 | Top-level project folder | `~/classes/neu502/oddball` |

---

## 04 · Get the Oddball PsychoPy Task

```bash
curl -L -H "Cache-Control: no-cache" \
  -o "./Psychopy-oddball-task.zip" \
  "https://www.dropbox.com/scl/fi/3x7r53n3js3i0hdv75p13/Psychopy-oddball-task.zip?rlkey=2e7zj1rkgol4t2ukz21748nml&dl=1"
```
