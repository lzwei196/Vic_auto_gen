# -*- coding: utf-8 -*-
import pandas as pd
from pathlib import Path
import os
import numpy as np
import warnings

# --- 0. Ignore unnecessary warnings ---
warnings.filterwarnings("ignore", category=FutureWarning)

# --- 1. Configure paths ---
# INPUT: Folder with your 649 daily forcing files in .txt format
DAILY_FORCING_DIR = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\forcing")
# OUTPUT: New folder for the 6-hourly forcing files
SUBDAILY_FORCING_DIR = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\forcing_6H")

# --- 2. Setup ---
print("Starting script to convert daily data to 6-hourly...")
if not DAILY_FORCING_DIR.exists():
    print(f"ERROR: Daily forcing directory not found at {DAILY_FORCING_DIR}"); exit()
os.makedirs(SUBDAILY_FORCING_DIR, exist_ok=True)
daily_files = list(DAILY_FORCING_DIR.glob("*"))
print(f"Found {len(daily_files)} daily files to process...")

# --- 3. Loop through each file ---
for i, daily_file in enumerate(daily_files):
    print(f"  ({i+1}/{len(daily_files)}) Processing: {daily_file.name}")
    
    # Read daily data
    df_daily = pd.read_csv(daily_file, sep='\t', header=None)
    df_daily.columns = ['air_temp', 'prec', 'pressure', 'swdown', 'lwdown', 'vp', 'wind']

    # Create an empty DataFrame for the new 6-hourly data
    df_subdaily = pd.DataFrame(index=np.arange(len(df_daily) * 4), columns=df_daily.columns)
    
    # --- 4. Disaggregate data and convert units ---
    # Air Temperature: Keep the daily value for all 4 sub-daily steps
    df_subdaily['air_temp'] = np.repeat(df_daily['air_temp'].values, 4)
    # Precipitation: Distribute the daily total evenly across the 4 time steps
    df_subdaily['prec'] = np.repeat(df_daily['prec'].values, 4) / 4.0
    # Pressure: Keep the daily value
    df_subdaily['pressure'] = np.repeat(df_daily['pressure'].values, 4)
    # Shortwave/Longwave Radiation: Assume constant flux density throughout the day
    df_subdaily['swdown'] = np.repeat(df_daily['swdown'].values, 4)
    df_subdaily['lwdown'] = np.repeat(df_daily['lwdown'].values, 4)
    # Vapor Pressure: Keep the daily value
    df_subdaily['vp'] = np.repeat(df_daily['vp'].values, 4)
    # Wind Speed: Keep the daily value
    df_subdaily['wind'] = np.repeat(df_daily['wind'].values, 4)
    
    # --- 5. Write the new 6-hourly file ---
    output_path = SUBDAILY_FORCING_DIR / daily_file.name
    df_subdaily.to_csv(output_path, sep='\t', header=False, index=False, float_format='%.4f')

print("\nData disaggregation complete!")
print(f"Generated {len(daily_files)} 6-hourly forcing files in: '{SUBDAILY_FORCING_DIR}'")