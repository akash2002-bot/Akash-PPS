import streamlit as st
import pandas as pd

st.set_page_config(page_title="PPS Sampling - Equal Width Binning", layout="centered")
st.title("📊 PPS Sampling with Equal Width Binning")

# Initialize session state
for key in ["df", "sampling_started", "column", "mode", "bin_col", "bin_weights", "sample_df"]:
    if key not in st.session_state:
        st.session_state[key] = None

# Step 1: File Upload
uploaded_file = st.file_uploader("Upload your CSV file", type="csv")
if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        st.session_state.df = df
        st.success("✅ File uploaded successfully.")
        st.write("### Preview of Uploaded Data")
        st.dataframe(df.head())
    except Exception as e:
        st.error(f"❌ Failed to read file: {e}")
        st.stop()

# Step 2: Select Column
if st.session_state.df is not None:
    numeric_columns = st.session_state.df.select_dtypes(include='number').columns.tolist()
    if not numeric_columns:
        st.error("No numeric columns found.")
        st.stop()

    st.session_state.column = st.selectbox("Select a numeric column for PPS sampling:", numeric_columns)

    if st.button("▶️ Run Sampling Setup"):
        st.session_state.sampling_started = True

# Step 3: Run Sampling Setup
if st.session_state.sampling_started and st.session_state.column:
    df = st.session_state.df
    column = st.session_state.column

    st.session_state.mode = st.radio("Choose sampling mode:", ["Automatic (based on values)", "Custom binning"], index=0)

    if st.session_state.mode == "Automatic (based on values)":
        filtered_df = df[df[column].notnull() & (df[column] > 0)].copy()
        if filtered_df.empty:
            st.error("No valid data found.")
            st.stop()
        filtered_df['probability'] = filtered_df[column] / filtered_df[column].sum()
        st.session_state.sample_ready_df = filtered_df
        st.session_state.bin_col = None

    else:
        # Step 4: Equal Width Binning
        num_bins = st.number_input("Step 1: Number of equal-width bins", min_value=2, value=3, step=1)
        try:
            bin_col = f"{column}_cut"
            df[bin_col] = pd.cut(df[column], bins=int(num_bins))
            st.session_state.bin_col = bin_col
            unique_bins = df[bin_col].cat.categories.astype(str).tolist()
        except Exception as e:
            st.error(f"Error in binning: {e}")
            st.stop()

        # Step 5: Weight Assignment
        default_weights = ",".join(["1.0"] * len(unique_bins))
        prob_input = st.text_input("Step 2: Assign weights to each bin (comma-separated):", value=default_weights)
        try:
            bin_weights = [float(w.strip()) for w in prob_input.split(",")]
            if len(bin_weights) != len(unique_bins):
                st.warning(f"Expected {len(unique_bins)} weights.")
                st.stop()
        except Exception as e:
            st.error(f"Invalid weights: {e}")
            st.stop()

        # Map weights and normalize
        prob_map = dict(zip(unique_bins, bin_weights))
        df['bin_label'] = df[bin_col].astype(str)
        df['probability'] = df['bin_label'].map(prob_map).astype(float)
        total = df['probability'].sum()
        if total == 0 or pd.isna(total):
            st.error("Total probability is zero or invalid.")
            st.stop()
        df['probability'] = df['probability'] / total
        st.session_state.sample_ready_df = df

    # Step 6: Sample Size and Sampling
    sample_df = None
    sample_size = st.number_input("Step 3: Enter sample size", min_value=1, max_value=len(st.session_state.sample_ready_df), step=1)

    if st.button("📌 Step 4: Sample Data"):
        try:
            sample_df = st.session_state.sample_ready_df.sample(
                n=sample_size,
                weights='probability',
                random_state=42
            ).reset_index(drop=True)
            st.session_state.sample_df = sample_df
            st.success("✅ Sampling completed.")
        except Exception as e:
            st.error(f"Sampling failed: {e}")

# Step 7: Display and Download
if st.session_state.sample_df is not None:
    st.subheader("🎯 Sampled Data Preview")
    preview_cols = [st.session_state.column, 'probability']
    if st.session_state.bin_col:
        preview_cols.insert(1, st.session_state.bin_col)
    st.dataframe(st.session_state.sample_df[preview_cols].head())

    csv = st.session_state.sample_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Sampled Data", data=csv, file_name="sampled_data.csv", mime="text/csv")
