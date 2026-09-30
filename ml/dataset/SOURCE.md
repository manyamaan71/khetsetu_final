# PlantVillage Training Data Source

The 9,006 original RGB images in this folder come from the public PlantVillage dataset.

- Dataset page: https://huggingface.co/datasets/mohanty/PlantVillage
- Source repository: https://github.com/spMohanty/PlantVillage-Dataset
- Configuration: `color`
- License declared in the Hugging Face dataset card: Creative Commons Attribution-ShareAlike 3.0 (CC BY-SA 3.0).
- Research citation: Mohanty, Hughes, and Salathé, "Using Deep Learning for Image-Based Plant Disease Detection," Frontiers in Plant Science 7 (2016), DOI: 10.3389/fpls.2016.01419.

Only these eight source folders are included, copied without image alteration and mapped to the KhetSetu class names:

| KhetSetu class folder | PlantVillage source folder | Images |
|---|---|---:|
| `Corn___Common_rust` | `Corn_(maize)___Common_rust_` | 1,192 |
| `Corn___healthy` | `Corn_(maize)___healthy` | 1,162 |
| `Potato___Early_blight` | `Potato___Early_blight` | 1,000 |
| `Potato___Late_blight` | `Potato___Late_blight` | 1,000 |
| `Potato___healthy` | `Potato___healthy` | 152 |
| `Tomato___Early_blight` | `Tomato___Early_blight` | 1,000 |
| `Tomato___Late_blight` | `Tomato___Late_blight` | 1,909 |
| `Tomato___healthy` | `Tomato___healthy` | 1,591 |

The dataset is redistributed under its declared share-alike license. Keep this attribution and license notice with copies of the dataset. The train/validation/test split is generated locally by `ml/training/prepare_dataset.py`; near-duplicate images are grouped before splitting.
