# KhetSetu — Final Report

This report records the current project state and this implementation pass. Metrics below were
regenerated from the included PlantVillage subset on 2026-09-30. The UI remains bilingual; the
requested Kannada, Telugu, Tamil, and Malayalam application translations are not implemented.

## 0. Summary of this pass

The project began with a real trained MobileNetV2 and evaluation pipeline, but did not include its
training corpus. This session:

1. Retrieved 9,006 original images for the eight supported classes from PlantVillage; source,
  attribution, license declaration, and source-to-project folder mapping are in §2.
2. Ran the duplicate-cluster-aware split: 6,301 train, 1,353 validation, 1,352 held-out test;
  zero duplicate clusters crossed splits.
3. Retrained ImageNet MobileNetV2 with class weighting, mild geometric/photometric augmentation,
  blur, motion blur, noise, and JPEG variation applied to training batches only. Exported Keras
  and TFLite; exact test-set Keras/TFLite predictions agree.
4. Evaluated the new model on the held-out test set: 95.34% accuracy and 0.9413 macro F1. Mild
  blur accuracy was 88.33%; limitations are listed in §§7-8 and `EVALUATION_REPORT.md`.
5. Added the canonical `model/class_names.json`; both backend and training validate its order
  against `class_config.json`.
6. Added `POST /api/report/pdf` and the existing Result-page download control. The endpoint
  re-runs the current image through the backend and supports safe low-confidence reports.
7. Added PDF font assets for six scripts, but complete app translations and PDF report copy remain
  English/Hindi only. Public translation services were not dependable in this environment.
8. Added report regression tests and ran backend/frontend checks; see §§13 and 17.

## 1. Architecture (unchanged, already correct)

```
image -> preprocessing (EXIF-rotate, RGB, 224x224 bilinear)
       -> leaf-pixel guard (rejects obvious non-leaf photos)
       -> MobileNetV2 classifier (model/khetsetu.tflite)
       -> temperature-scaled softmax -> argmax -> class_names[index]
       -> 0.70 confidence gate (backend-enforced; no diagnosis leaves the server below it)
       -> data/guidance.json lookup (trusted, human-written; independent of the model)
       -> [optional] Gemini rewrites the guidance into 2-3 simple sentences (additive only)
       -> existing React UI (unchanged)
```

## 2. Dataset

- Dataset: PlantVillage `color` configuration, obtained from the public source repository
  https://github.com/spMohanty/PlantVillage-Dataset and dataset card
  https://huggingface.co/datasets/mohanty/PlantVillage.
- The Hugging Face dataset metadata declares CC BY-SA 3.0; `ml/dataset/SOURCE.md` preserves source
  URLs, attribution, citation, license declaration, original folder names and image counts.
- Included subset: 9,006 original images in the eight classes below. No synthetic training images
  or invented labels were used.
- Deduplication grouped 292 images in 119 clusters; no cross-class duplicate hashes were found.
  The train/validation/test split is by duplicate cluster with a 70/15/15 target ratio.

## 3. Classes used (8)

| class_name | crop | condition |
|---|---|---|
| `Corn___Common_rust` | Corn | Common Rust |
| `Corn___healthy` | Corn | Healthy |
| `Potato___Early_blight` | Potato | Early Blight |
| `Potato___Late_blight` | Potato | Late Blight |
| `Potato___healthy` | Potato | Healthy |
| `Tomato___Early_blight` | Tomato | Early Blight |
| `Tomato___Late_blight` | Tomato | Late Blight |
| `Tomato___healthy` | Tomato | Healthy |

## 4. Number of images per class / train-val-test counts

Per-class source counts and split counts are in `ml/dataset/SOURCE.md` and
`ml/dataset_split/split_summary.json`. Split sizes used for the shipped model:

- Train: 6,301 images
- Validation: 1,353 images
- Test: 1,352 images (held out from training, checkpoint selection, and calibration)

## 5. Model architecture

MobileNetV2 (alpha=1.0), ImageNet-pretrained, input 224×224×3 raw RGB (rescaling to [-1,1] is
built into the model graph). Head: `GlobalAveragePooling2D -> Dropout(0.3) -> Dense(8, softmax)`.
Full details: README.md §5.

## 6. Training configuration

3 frozen-base epochs with `Adam(1e-3)`, followed by 2 fine-tuning epochs from MobileNetV2 layer 120
with `Adam(1e-4)`; sparse categorical cross-entropy and balanced class weights computed only from
the training split. Train-only augmentation: horizontal flip, rotation 0.08, zoom 0.12, brightness
and contrast 0.15, 25% mild Gaussian/motion blur, 25% mild sensor noise, and 20% JPEG recompression
(quality 72-96). `ModelCheckpoint` keeps the best validation-accuracy weights; `EarlyStopping`
(patience 3) and `ReduceLROnPlateau` are configured. Best validation checkpoint was epoch 2 of
fine-tuning. Temperature 1.1324 was fitted using validation data only.

## 7. Accuracy, Precision, Recall, F1 (held-out TEST split, n=1,352)

| metric | value |
|---|---|
| Accuracy | 0.9534 |
| Macro precision / recall / F1 | 0.9313 / 0.9582 / 0.9413 |
| Weighted precision / recall / F1 | 0.9561 / 0.9534 / 0.9535 |
| Calibration (ECE) | 0.0132 before; 0.0147 after temperature scaling (T=1.1324) |

Per-class (precision / recall / F1 / support):

| class | precision | recall | F1 | support |
|---|---|---|---|---|
| Corn___Common_rust | 0.989 | 1.000 | 0.994 | 179 |
| Corn___healthy | 1.000 | 1.000 | 1.000 | 174 |
| Potato___Early_blight | 1.000 | 0.987 | 0.993 | 150 |
| Potato___Late_blight | 0.965 | 0.907 | 0.935 | 150 |
| Potato___healthy | 0.719 | 1.000 | 0.836 | 23 |
| Tomato___Early_blight | 0.903 | 0.867 | 0.884 | 150 |
| Tomato___Late_blight | 0.974 | 0.906 | 0.939 | 287 |
| Tomato___healthy | 0.902 | 1.000 | 0.948 | 239 |

The full report, confusion matrix, confidence threshold trade-offs, blur/dark/JPEG robustness, and
synthetic non-leaf check are in `ml/evaluation/results/`.

## 8. Confusion matrix

Full matrix: `ml/evaluation/results/confusion_matrix.csv` (and `.png`). Top confusions (all between
visually similar blight types, none involving a random/unrelated class):

| true | predicted | count |
|---|---|---|
| Tomato___Early_blight | Tomato___healthy | 14 |
| Tomato___Late_blight | Tomato___healthy | 11 |
| Tomato___Late_blight | Tomato___Early_blight | 10 |
| Potato___Late_blight | Potato___healthy | 9 |

## 9. Root cause of the reported "repeated Tomato Late Blight" bug

**This bug did not reproduce against the shipped model and current code.** Re-running inference on
all 16 held-out sample photos (§13 below) through the actual production code path gave correct,
varied predictions across all 8 classes — not a single stuck class.

What was found and fixed, which is a plausible cause of exactly this symptom if a different config
file had been used to set up the backend:

- `backend/.env.example` was stale: `MODEL_PATH=./models/khetsetu_model.keras` (wrong folder name —
  the real folder is `model/`, singular — and a filename that never existed) combined with
  `DEMO_MODE=true`. If a developer copied that file to `backend/.env` instead of the project-root
  `.env.example`, `DEMO_MODE=true` forces the **simulated demo predictor**
  (`Classifier._demo()` in `backend/app/model.py`), which returns a random class seeded by the
  image's SHA-256 hash. This is clearly labelled `"demo_mode": true` in the API response and is not
  the "confident wrong diagnosis" bug described, but it is the one real inconsistency found in the
  project that could cause confusing, non-representative results if the wrong template were used.
  **Fixed**: `backend/.env.example` now matches `backend/app/config.py` exactly (empty
  `MODEL_PATH` = auto-detect, `DEMO_MODE=false`), and both `.env.example` files are internally
  consistent.
- Everything else on the bug checklist was specifically audited and found correct: `model.py` loads
  the model exactly once at startup (`main.py` lifespan, not per-request); canonical
  `class_names.json` matches both `class_config.json` order and model output width (checked at load time —
  `if n_out != len(class_names()): raise RuntimeError(...)`); `preprocessing.py`'s resize/rescale
  path is identical to `ml/training/common.py`'s (both documented as required to match, in comments
  in both files); the frontend (`api.ts`, `Scan.tsx`, `Result.tsx`) sends a fresh `FormData` request
  per photo with no client-side caching, `localStorage`, or hardcoded result — `grep` across
  `frontend/src` for "Late Blight" / "hardcod" / "mock" only matches translation strings, not logic.

## 10. Exact model path / class_names path / API endpoint

- Model: `model/khetsetu.tflite` (falls back to `model/khetsetu.keras`), auto-detected by
  `backend/app/model.py::Classifier._find_model_file()`.
- Class names / order: `model/class_names.json` (canonical order, read by training and the backend;
  both validate consistency with `model/class_config.json`).
- Prediction endpoint: `POST /api/predict` (multipart: `image`, `language`), implemented in
  `backend/app/api/predict.py` → `backend/app/services/analysis_service.py`.
- PDF endpoint: `POST /api/report/pdf` (multipart: current `image`, `language`); the backend
  re-runs inference and creates an English/Hindi PDF without trusting client prediction fields.

## 11. Gemini integration

See README.md §13 for the full architecture diagram. Summary: Gemini (`gemini-1.5-flash`) is called
only if `GEMINI_API_KEY` is set; it receives the already-decided crop/disease/confidence plus the
matching `guidance.json` text and is instructed to use only those facts, in 2-3 simple sentences, in
English or Hindi, with no pesticide names/dosages. Output is additive
(`result.extra_explanation`); the `guidance` object in the API response always comes from
`guidance.json` regardless of whether Gemini ran. `explanation_source` is `"guidance"` or
`"guidance+llm"` depending on whether Gemini succeeded.

## 12. Gemini fallback test

Verified by running the full test suite and `backend/test_model.py` with `GEMINI_API_KEY` unset
(the shipped `.env.example` files ship it empty, and no `.env` file is included in this ZIP): the
classifier, confidence gate, and guidance lookup all work identically; `is_available()` returns
`False` and `generate_extra_explanation()` returns `None` without making a network call, so
`analysis_service.py` simply omits `extra_explanation` and reports `explanation_source: "guidance"`.

## 13. End-to-end and robustness checks

- Held-out test: 1,352 images, 95.34% top-1 accuracy; per-class results are in §7 and
  `ml/evaluation/results/class_report.csv`.
- Mild Gaussian blur (radius 2.5), 300 held-out images: 88.33% top-1 accuracy; 89% answered at the
  0.70 threshold, with 91.39% accuracy among answered images.
- Darkened images: 91.00% top-1, 89.67% answered. Low-JPEG quality: 87.00% top-1, 89.67% answered.
- 200 synthetic non-leaf images: 134 rejected by the color guard; 50 still passed both guard and
  confidence threshold. The heuristic is not a reliable general-purpose leaf detector.
- Healthy-potato test support is only 23 images; measured precision is 0.719. More independent data
  is needed before field deployment claims.
- Fresh-result report test posts a fake client disease/confidence but verifies the PDF uses the
  server's healthy tomato prediction. Low-confidence report test verifies disease/crop names are
  absent. Font-shaping test generates PDF text samples for all six bundled scripts.
- Backend suite: **49 passed** (includes real-model PDF integration checks). Frontend `npm run build` passes.
- Browser TTS and PDF visual rendering on actual devices, live Gemini calls, and all-six-language
  content/PDF tests were not performed. The UI and guidance currently support English and Hindi only.

## 14. Low-confidence behavior

Confirmed and correct: any prediction below `CONFIDENCE_THRESHOLD` (0.70) returns
`is_confident: false`, `prediction: null`, `guidance: null`, and a translated "Photo unclear" message
— no crop or disease name is ever included in that response (`analysis_service.py`).
The PDF route independently re-runs the current image through the same gate. Below threshold it
creates a photo-unclear report with photo tips and no disease diagnosis.

## 15. Files changed this session

- `ml/dataset/` — 9,006 PlantVillage images across eight supported classes, plus source/license
  documentation.
- `model/khetsetu.keras`, `model/khetsetu.tflite`, `model/model_meta.json` — retrained, exported,
  calibrated MobileNetV2 and metadata.
- `model/class_names.json`, `backend/app/disease_info.py`, `ml/training/common.py` — canonical
  class-output order and checks.
- `ml/training/train.py`, `backend/requirements.txt` — training-only camera augmentations and
  missing ML/PDF dependencies.
- `ml/evaluation/results/` — regenerated held-out metrics, per-class report, confusion matrix,
  threshold analysis, latency and robustness report.
- `backend/app/api/report.py`, `backend/app/services/report_service.py` — fresh-image PDF endpoint,
  English/Hindi report generation, confidence visualization, safe unclear reports.
- `backend/assets/fonts/` — SIL OFL Noto fonts and license, with HarfBuzz support for six scripts.
- `frontend/src/pages/Scan.tsx`, `frontend/src/pages/Result.tsx`, `frontend/src/services/api.ts`,
  `frontend/src/services/storageService.ts`, `frontend/src/types/index.ts`,
  `frontend/src/data/translations.ts` — current-image persistence, PDF request/download and minimal
  Result-page controls.
- `tests/test_report.py`, `tests/test_backend.py`, `README.md`, `ml/dataset/README.md`, and this
  report — regression coverage and updated project documentation.

## 16. Exact commands to run

```powershell
cd khetsetu\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy ..\.env.example .env
uvicorn app.main:app --reload
```

```powershell
cd khetsetu\frontend
npm install
npm run dev
```

```powershell
cd khetsetu
pytest tests -v
cd backend
python test_model.py ..\tests\samples\Tomato___Late_blight\sample_1.jpg
```

## 17. End-to-end test summary

| check | result |
|---|---|
| Real model loads and is used (not demo) | ✅ `DEMO_MODE=false`, model loads from `model/khetsetu.tflite` |
| Public dataset obtained and documented | ✅ 9,006 PlantVillage images, CC BY-SA 3.0 declared by dataset card |
| Leakage-aware split | ✅ 6,301 train / 1,353 validation / 1,352 test; zero duplicate clusters cross splits |
| Held-out accuracy / macro F1 | ✅ 95.34% / 0.9413; caveats in §7 |
| Mild-blur test | ✅ 88.33% accuracy; 89% answered at the 0.70 threshold |
| Repeated "always Late Blight" bug | ✅ class output order verified; no hardcoded disease; tests assert server output authority |
| Confidence threshold enforced server-side | ✅ verified in code and by test suite |
| PDF current-scan integrity and low-confidence redaction | ✅ 3 endpoint/font tests pass |
| PDFs in English and Hindi | ✅ generated with embedded Noto fonts; automated text extraction has shaping-mapping limitations |
| Kannada/Telugu/Tamil/Malayalam app translations | ❌ not implemented; fonts alone do not provide translated content |
| Gemini additive-only, never classifies | ✅ by construction — only receives an already-decided prediction |
| Gemini fallback works with no key | ✅ `explanation_source: "guidance"`, no crash, no network call attempted |
| English/Hindi UI and guidance | ✅ preserved |
| Existing UI preserved | ✅ only the requested PDF control was added; frontend build passes |
| Backend test suite | ✅ 49 passed |
| Final ZIP created | Not created: the hard six-language content/PDF requirement is incomplete, so this source state is not labeled as the requested complete deliverable |
