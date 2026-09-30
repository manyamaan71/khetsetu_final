# KhetSetu model evaluation (held-out test split, n=1352)

- **Accuracy:** 0.9534
- **Macro** precision / recall / F1: 0.9313 / 0.9582 / 0.9413
- **Weighted** precision / recall / F1: 0.9561 / 0.9534 / 0.9535
- Model size: {'keras_mb': 9.65, 'tflite_mb': 8.91}
- Avg inference (batch 1): Keras 251.2 ms; TFLite 13.2 ms
- Calibration (ECE): 0.0132 -> 0.0147 after temperature scaling (T=1.1324)

## Per-class

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

## Confidence threshold trade-off

| threshold | answered | accuracy when answered | wrong answers shown | correct answers withheld |
|---|---|---|---|---|
| 0.5 | 0.9889 | 0.9596 | 54 | 6 |
| 0.6 | 0.9697 | 0.9672 | 43 | 21 |
| 0.7 | 0.9497 | 0.9727 | 35 | 40 |
| 0.8 | 0.9231 | 0.9848 | 19 | 60 |
| 0.9 | 0.8706 | 0.9881 | 14 | 126 |
| 0.95 | 0.824 | 0.9937 | 7 | 182 |

## Robustness to degraded photos

| degradation | accuracy | answered @thr | accuracy when answered |
|---|---|---|---|
| blur | 0.8833 | 0.89 | 0.9139 |
| dark | 0.91 | 0.8967 | 0.9665 |
| bright | 0.93 | 0.9467 | 0.9507 |
| low_jpeg | 0.87 | 0.8967 | 0.9219 |
| small_crop | 0.6833 | 0.7667 | 0.8043 |

## Non-leaf images

```json
{
  "leaf_guard_min_ratio": 0.08,
  "real_test_leaves_wrongly_rejected_by_guard": 0,
  "real_test_leaves_total": 1352,
  "synthetic_non_leaf_images": 200,
  "synthetic_rejected_by_leaf_guard": 134,
  "synthetic_passing_guard_and_threshold_(false_diagnosis)": 50,
  "synthetic_passing_threshold_without_guard": 161
}
```

**Caveat:** Test images come from the same lab-style dataset as training (split by duplicate cluster). Accuracy on real field photos (cluttered background, sunlight, different cameras) is expected to be LOWER.

## Top confusions

- 14x  Tomato___Early_blight  ->  Tomato___healthy
- 11x  Tomato___Late_blight  ->  Tomato___healthy
- 10x  Tomato___Late_blight  ->  Tomato___Early_blight
- 9x  Potato___Late_blight  ->  Potato___healthy
- 5x  Tomato___Early_blight  ->  Tomato___Late_blight
- 4x  Tomato___Late_blight  ->  Potato___Late_blight
- 2x  Tomato___Late_blight  ->  Corn___Common_rust
- 2x  Potato___Late_blight  ->  Tomato___Late_blight

## TFLite model
```json
{
  "accuracy": 0.9534,
  "macro_f1": 0.9413,
  "agreement_with_keras": 1.0,
  "avg_inference_ms_batch1": 13.2
}
```