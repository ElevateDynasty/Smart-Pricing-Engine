# Training the ApexPricing ML Demand Forecaster in Google Colab

This guide provides step-by-step instructions on how to train, evaluate, and export the Monotone LightGBM Demand Forecaster and Price Elasticity Estimator using **Google Colab**.

---

## Method 1: Ready-Made Jupyter Notebook (Easiest)

We have included a pre-configured notebook ready for Colab: [`notebooks/Smart_Pricing_Colab_Training.ipynb`](file:///c:/Users/gaura/OneDrive/Desktop/Technical%20Seminar%20project/AI%20PRice%20recomm/notebooks/Smart_Pricing_Colab_Training.ipynb).

1. Open [Google Colab](https://colab.research.google.com).
2. Click **File** > **Upload notebook**.
3. Select `notebooks/Smart_Pricing_Colab_Training.ipynb` from your local folder.
4. Run the cells sequentially from top to bottom.

---

## Method 2: 1-Click Repo Clone in Colab

1. Open a blank notebook at [Google Colab](https://colab.research.google.com).
2. Set Runtime to **Python 3** (GPU is optional; CPU trains in ~5 seconds).
3. In the first code cell, clone your repository and install dependencies:

```python
# Cell 1: Clone Repository & Install Dependencies
!git clone https://github.com/ElevateDynasty/Smart-Pricing-Engine.git
%cd Smart-Pricing-Engine
!pip install -q -r requirements.txt
```

4. In the second cell, execute the training pipeline:

```python
# Cell 2: Train LightGBM Model & Price Elasticity
!python scripts/train_colab.py
```

5. Download the trained model back to your local repository:

```python
# Cell 3: Download Model File
from google.colab import files
files.download('models_saved/demand_forecaster_lightgbm.joblib')
```

Place the downloaded file into your local project's `models_saved/` folder.

---

## Method 2: Training on Real Kaggle Mobile Phone Dataset

To train specifically on real Kaggle smartphone and consumer electronics sales:

```python
# In Colab terminal / cell:
!python main.py --kaggle
```

This will automatically load `data/raw/mobile_phones.csv`, run the `KaggleDemandAdapter`, perform a temporal train/validation split, evaluate metrics, and save:
`models_saved/demand_forecaster_kaggle.joblib`

You can then download it with:
```python
files.download('models_saved/demand_forecaster_kaggle.joblib')
```

---

## Method 3: Direct Standalone Interactive Colab Notebook

If you prefer running step-by-step without cloning git, you can copy-paste the cells below into any blank Colab notebook:

### Step 1: Install Required Packages
```python
!pip install -q lightgbm scikit-learn pandas numpy statsmodels joblib
```

### Step 2: Upload Project Source
Upload the `src/` folder (or a zipped `src.zip` archive) into Colab's file explorer:
```python
!unzip -q src.zip
```

### Step 3: Run Training & View Metrics
```python
from src.data.data_pipeline import DataPipeline
from src.models.demand_forecaster import DemandForecaster
from src.models.elasticity_estimator import ElasticityEstimator

# 1. Build unified electronic sales dataset
dp = DataPipeline()
df = dp.build_unified_dataset()
print(f"Dataset Size: {len(df)} records")

# 2. Train Monotone LightGBM
forecaster = DemandForecaster(model_type="lightgbm")
metrics = forecaster.fit(df)
print(f"Validation MAE : {metrics['mae']} units/day")
print(f"Validation RMSE: {metrics['rmse']} units/day")
print(f"Validation R^2 : {metrics['r2']:.4f}")

# 3. Fit Price Elasticity
elasticity = ElasticityEstimator()
el_dict = elasticity.fit(df)
print(f"Trained elasticity across {len(el_dict)} electronic devices.")
```

---

## Key Econometric Features Enforced During Training

1. **Law of Demand (Monotone Constraints):**
   - Price increases cannot artificially increase demand:
   - `price_ratio_mrp`: `monotone = -1`
   - `price_ratio_comp`: `monotone = -1`
   - `price_delta_comp`: `monotone = -1`
2. **Conformal Uncertainty Quantification:**
   - Evaluates P10 (lower) and P90 (upper) demand uncertainty bands.
3. **Finite-Horizon Inventory Dynamics:**
   - Evaluates holding cost against terminal obsolescence penalties.
