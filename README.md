# CT Quality Review

A small desktop application for reviewing local 3D CT NIfTI files (`.nii` and `.nii.gz`) and writing quality decisions to a CSV report.

## Features

- Folder-based review of `.nii` and `.nii.gz` files.
- Three synchronized-independent anatomical views: axial, coronal, sagittal.
- One slice slider per view.
- Two-handle HU range control for display windowing.
- Optional physical-aspect display. By default, views fill their panels for fast visual review.
- Accept, reject, or skip each CT.
- Left and right arrow keys move to the previous and next CT.
- Optional comment per decision.
- Required quality checklist for accept/reject decisions.
- Accept requires abdomen/pelvis and sufficient z-axis to be Yes.
- Reject requires abdomen/pelvis or sufficient z-axis to be No, or artifacts/problems to be Yes.
- Existing CSV reports are resumed.
- Startup screen has separate report actions for loading an existing CSV or creating a new one.
- Optional outcome JSON can be loaded and displayed per matched CT file.
- Decisions are saved by file name and overwritten when reviewed again.
- Configurable minimum axial slice warning.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

On macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```powershell
python app.py
```

## Schermata iniziale

Nella schermata iniziale bisogna scegliere la cartella che contiene i file CT in formato `ct.nii.gz`/`.nii.gz`, organizzati senza sottocartelle e con nomi come:

```text
my_folder/
CT_IEO201796.nii.gz
CT_IEO201795.nii.gz
...
```

Poi si puo scegliere un dataset JSON da cui estrarre i metadati di outcome. I record devono avere una struttura simile a questa:

```json
[
  {
    "record_id": "IEO 2009-1",
    "treatment": "PDS",
    "CRS": null,
    "kelim_score": null,
    "sensitivity": "Yes",
    "overall_survival": "DOD (dead of disease)",
    "complications": null,
    "residual_tumor": "Yes"
  },
  {...},
  {...}
]
```

Sempre dalla schermata iniziale bisogna indicare dove salvare il CSV della review, oppure caricare un CSV esistente se una review è gia stata iniziata ma non e ancora terminata. Si deve inoltre scegliere il numero minimo di slice assiali che una TAC deve avere per essere considerata accettabile secondo questo parametro.

## Schermata di review
Durante la review, prima di premere **Accept** o **Reject** bisogna compilare i checkbox della checklist di qualita; altrimenti il caso può essere skippato e si puo tornare a valutarlo in seguito. Ci si puo muovere tra le CT anche tramite il menu a comparsa dei file. A ogni **Skip**, **Accept** o **Reject**, il file viene aggiunto o aggiornato nel CSV.
![Schermata di review](images/review_screen.PNG)

## CSV Columns

```csv
file_name,file_path,status,comment,z_slices,include_abdomen_pelvis,include_head,include_chest,sufficient_z_axis,artifacts_or_technical_issues,reviewed_at
```

`file_path` is relative to the selected NIfTI folder. `status` is one of `accepted`, `rejected`, or `skipped`.

## Notes

The app reads `.nii.gz` directly. If loading compressed files becomes slow on your dataset, the next optimization should be adding an optional local cache that stores decompressed volumes for faster reopening.
