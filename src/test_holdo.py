import sys
import os
import pandas as pd

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.data_loader import DataLoader

def test_holdo_fetch():
    print("Initializing DataLoader...")
    loader = DataLoader()
    
    print("Fetching Holdo Chile Smart Fund data (limit=365)...")
    df = loader.fetch_holdo_data(limit=365)
    
    if df is not None:
        print("Success!")
        print(f"Shape: {df.shape}")
        print("Last 5 rows:")
        print(df.tail())
        print("Data Types:")
        print(df.dtypes)
    else:
        print("Failed to fetch Holdo data.")

if __name__ == "__main__":
    test_holdo_fetch()
