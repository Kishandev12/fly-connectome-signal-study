from pathlib import Path
import pandas as pd

DATA = Path(__file__).parent / "data" / "Connectivity_783.parquet"

if not DATA.exists():
    raise SystemExit(f"Connectome file not found: {DATA}")

connections = pd.read_parquet(DATA)
print(f"Rows (connections): {len(connections):,}")
print("Columns:", ", ".join(connections.columns))
print("\nFirst five rows:")
print(connections.head().to_string(index=False))
print("\nLargest outgoing connection counts:")
pre_col = "Presynaptic_Index"
post_col = "Postsynaptic_Index"
if pre_col in connections and post_col in connections:
    print(connections.groupby(pre_col).size().nlargest(10).to_string())
else:
    print("The column names differ from the expected Shiu model format; inspect the columns above.")

