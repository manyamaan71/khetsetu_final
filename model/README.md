# model/

| file | what it is |
|---|---|
| `class_names.json` | **Canonical ordered model-output labels**. Backend and training read this file and verify it matches `class_config.json`. Never reorder labels without retraining. |
| `class_config.json` | Crop/disease display names (EN+HI), source folders, and healthy flags, indexed in the same order as `class_names.json`. |
| `khetsetu.tflite` | Deployment model used by the backend (TensorFlow Lite). |
| `khetsetu.keras` | Same model as a Keras file (fallback loader, used by `evaluate.py`). |
| `model_meta.json` | Training details, temperature used to calibrate confidence, validation accuracy. |
| `training_history.json` | Loss/accuracy per epoch. |

Input: float32 `(1, 224, 224, 3)`, RAW RGB pixel values 0-255 (scaling to [-1, 1] is inside the model).
Output: 8 softmax probabilities in `class_names.json` order.
