import pandas as pd
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox

# Setup GUI
root = tk.Tk()
root.withdraw()

# Step 1: File selection
file_path = filedialog.askopenfilename(title="Select your CSV file")
if not file_path:
    messagebox.showerror("Error", "No file selected.")
    exit()

try:
    df = pd.read_csv(file_path)
except Exception as e:
    messagebox.showerror("Error", f"Failed to read file:\n{e}")
    exit()

# Step 2: Column to bin
column = simpledialog.askstring("Column", "Enter the column name to bin:")
if column is None or column not in df.columns:
    messagebox.showerror("Error", f"Column '{column}' not found or cancelled.")
    exit()

# Step 3: Choose binning method
auto_mode = messagebox.askyesno("Binning Mode", "Do you want to use automatic PPS sampling without custom bins?")

if auto_mode:
    # Auto mode: use raw column values as weights directly
    try:
        df = df[df[column].notnull() & (df[column] > 0)].copy()
        df['probability'] = df[column] / df[column].sum()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to calculate automatic PPS weights:\n{e}")
        exit()
    bin_col = None
else:
    # Custom bin mode
    try:
        num_bins = int(simpledialog.askstring("Bins", "Enter number of equal-frequency bins (e.g., 3):"))
    except:
        messagebox.showerror("Error", "Invalid number of bins.")
        exit()

    labels_input = simpledialog.askstring("Labels", f"Enter {num_bins} labels (comma-separated):")
    labels = [l.strip() for l in labels_input.split(",") if l.strip()]
    if len(labels) != num_bins:
        messagebox.showerror("Error", f"Expected {num_bins} labels, got {len(labels)}.")
        exit()

    bin_col = f"{column}_qbin"
    try:
        df[bin_col] = pd.qcut(df[column], q=num_bins, labels=labels)
    except Exception as e:
        messagebox.showerror("Error", f"qcut failed:\n{e}")
        exit()

    prob_input = simpledialog.askstring("Probabilities", f"Enter sampling weights for bins (comma-separated):")
    try:
        bin_weights = [float(w.strip()) for w in prob_input.split(",")]
        if len(bin_weights) != num_bins:
            raise ValueError("Mismatch in weight count.")
    except Exception as e:
        messagebox.showerror("Error", f"Invalid weights:\n{e}")
        exit()

    prob_map = dict(zip(labels, bin_weights))
    df['probability'] = df[bin_col].map(prob_map).astype(float)

    total = df['probability'].sum()
    if total == 0 or pd.isna(total):
        messagebox.showerror("Error", "Total probability is zero or invalid.")
        exit()
    df['probability'] = df['probability'] / total

# Step 4: Sample
try:
    sample_size = int(simpledialog.askstring("Sample Size", "Enter sample size (e.g., 50):"))
except:
    messagebox.showerror("Error", "Invalid sample size.")
    exit()

if sample_size > len(df):
    messagebox.showerror("Error", f"Sample size ({sample_size}) exceeds available records ({len(df)}).")
    exit()

try:
    sample_df = df.sample(n=sample_size, weights='probability', random_state=42).reset_index(drop=True)
except Exception as e:
    messagebox.showerror("Error", f"Sampling failed:\n{e}")
    exit()

# Step 5: Preview
print("\u2705 Sampled data preview:")
preview_cols = [column, 'probability'] if bin_col is None else [column, bin_col, 'probability']
print(sample_df[preview_cols].head())

# Step 6: Save output
save_path = filedialog.asksaveasfilename(
    title="Save sampled data",
    defaultextension=".csv",
    filetypes=[("CSV files", "*.csv")]
)
if save_path:
    sample_df.to_csv(save_path, index=False)
    print(f"\u2705 Sample saved to: {save_path}")
else:
    print("\u26A0 Save cancelled.")
