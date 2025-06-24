import streamlit as st
import pandas as pd

st.set_page_config(page_title="PPS Sampling - Equal Width Binning", layout="centered")
st.title("📊 PPS Sampling with Equal Width Binning")

if "sampling_started" not in st.session_state:
    st.session_state.sampling_started = False
if "df" not in st.session_state:
    st.session_state.df = None
if "bin_col" not in st.session_state:
    st.session_state.bin_col = None
if "mode" not in st.session_state:
    st.session_state.mode = None
if "column" not in st.session_state:
    st.session_state.column = None

uploaded_file = st.file_uploader("Upload your CSV file", type="csv")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        st.session_state.df = df
        st.success("✅ File uploaded successfully.")
    except Exception as e:
        st.error(f"Failed to read file: {e}")
        st.stop()

    df = st.session_state.df
    st.write("### Preview of Uploaded Data")
    st.dataframe(df.head())

    numeric_columns = df.select_dtypes(include='number').columns.tolist()
    if not numeric_columns:
        st.error("No numeric columns found.")
        st.stop()

    st.session_state.column = st.selectbox("Select a numeric column for PPS sampling:", numeric_columns)

    if st.button("▶️ Run Sampling Setup"):
        st.session_state.sampling_started = True

if st.session_state.sampling_started and st.session_state.df is not None:
    df = st.session_state.df
    column = st.session_state.column

    st.session_state.mode = st.radio("Choose sampling mode:", ["Automatic (based on values)", "Custom binning"])

    if st.session_state.mode == "Automatic (based on values)":
        df = df[df[column].notnull() & (df[column] > 0)].copy()
        if df.empty:
            st.error("No valid data found.")
            st.stop()
        df['probability'] = df[column] / df[column].sum()
        st.session_state.bin_col = None

    else:
        num_bins = st.number_input("Step 1: Number of equal-width bins", min_value=2, step=1)
        try:
            bin_col = f"{column}_cut"
            df[bin_col] = pd.cut(df[column], bins=int(num_bins))
            st.session_state.bin_col = bin_col
        except Exception as e:
            st.error(f"Error in binning: {e}")
            st.stop()

        unique_bins = df[bin_col].cat.categories.astype(str).tolist()
        st.markdown("Step 2: Assign weights to each bin")
        default_weights = ",".join(["1.0"] * len(unique_bins))
        prob_input = st.text_input("Enter weights (comma-separated)", value=default_weights)
        try:
            bin_weights = [float(w.strip()) for w in prob_input.split(",")]
            if len(bin_weights) != len(unique_bins):
                st.warning(f"Expected {len(unique_bins)} weights.")
                st.stop()
        except Exception as e:
            st.error(f"Invalid weights: {e}")
            st.stop()

        prob_map = dict(zip(unique_bins, bin_weights))
        df['bin_label'] = df[bin_col].astype(str)
        df['probability'] = df['bin_label'].map(prob_map).astype(float)
        total = df['probability'].sum()
        if total == 0 or pd.isna(total):
            st.error("Total probability is zero or invalid.")
            st.stop()
        df['probability'] = df['probability'] / total

    sample_size = st.number_input("Step 3: Enter sample size", min_value=1, max_value=len(df), step=1, key="sample_size_input")

    if st.button("📌 Step 4: Sample Data"):
        try:
            sample_df = df.sample(n=sample_size, weights='probability', random_state=42).reset_index(drop=True)
            st.success("✅ Sampling completed.")
            preview_cols = [column, 'probability']
            if st.session_state.bin_col:
                preview_cols.insert(1, st.session_state.bin_col)
            st.dataframe(sample_df[preview_cols].head())

            csv = sample_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Sampled Data", data=csv, file_name="sampled_data.csv", mime="text/csv")
        except Exception as e:
            st.error(f"Sampling failed: {e}")
