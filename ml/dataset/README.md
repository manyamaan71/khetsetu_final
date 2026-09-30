# PlantVillage source subset

This folder includes the original PlantVillage color images for KhetSetu's eight supported classes.
Source names were mapped to the model's stable folder names without altering image contents.
See `SOURCE.md` for the dataset URL, license, citation, class mapping, and per-class image counts.

The source images are not modified by the split or training scripts. Generated split files and image caches go to
`ml/dataset_split/` and `ml/cache/` respectively; those generated folders are excluded from source packaging.

The full dataset is not included in this project ZIP to keep it a reasonable size (see README.md section 17).
