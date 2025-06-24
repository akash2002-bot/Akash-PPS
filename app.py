import streamlit as st
import pandas as pd

st.set_page_config(page_title="PPS Sampling with Binning", layout="centered")

st.title("📊 PPS Sampling with Binning")

# Step 1: Upload CSV file
uploaded_file = st.file_uploader("Upload your CSV file", type="csv")
if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.success("File uploaded successfully.")
    except Exception as e:
        st.error(f"Failed to read file: {e}")
        st.stop()

    st.write("### Preview of Data")
    st.dataframe(df.head())

    # Step 2: Column input
    column = st.selectbox("Select the column name to use for PPS sampling:", df.columns)

    if df[column].isnull().all():
        st.error("Selected column contains only null values.")
        st.stop()

    # Step 3: Choose binning mode
    auto_mode = st.radio("Choose sampling mode:", ["Automatic (based on column values)", "Custom binning"])

    if auto_mode == "Automatic (based on column values)":
        try:
            df = df[df[column].notnull() & (df[column] > 0)].copy()
            df['probability'] = df[column] / df[column].sum()
        except Exception as e:
            st.error(f"Automatic PPS weight calculation failed: {e}")
            st.stop()
        bin_col = None
    else:
        num_bins = st.number_input("Enter number of equal-frequency bins:", min_value=2, step=1)
        labels_input = st.text_input(f"Enter {int(num_bins)} labels (comma-separated):", value="Low,Medium,High")
        labels = [l.strip() for l in labels_input.split(",") if l.strip()]
        if len(labels) != int(num_bins):
            st.error(f"Expected {int(num_bins)} labels, got {len(labels)}.")
            st.stop()

        bin_col = f"{column}_qbin"
        try:
            df[bin_col] = pd.qcut(df[column], q=int(num_bins), labels=labels)
        except Exception as e:
            st.error(f"qcut failed: {e}")
            st.stop()

        weight_input = st.text_input(f"Enter {int(num_bins)} sampling weights (comma-separated):", value="0.2,0.5,0.3")
        try:
            bin_weights = [float(w.strip()) for w in weight_input.split(",")]
            if len(bin_weights) != int(num_bins):
                st.error(f"Expected {int(num_bins)} weights, got {len(bin_weights)}.")
                st.stop()
        except Exception as e:
            st.error(f"Invalid weight input: {e}")
            st.stop()

        prob_map = dict(zip(labels, bin_weights))
        df['probability'] = df[bin_col].map(prob_map).astype(float)
        total = df['probability'].sum()
        if total == 0 or pd.isna(total):
            st.error("Total probability is zero or invalid.")
            st.stop()
        df['probability'] = df['probability'] / total

    # Step 4: Sampling
    sample_size = st.number_input("Enter sample size:", min_value=1, max_value=len(df), step=1)
    if st.button("Sample Data"):
        try:
            sample_df = df.sample(n=sample_size, weights='probability', random_state=42).reset_index(drop=True)
        except Exception as e:
            st.error(f"Sampling failed: {e}")
            st.stop()

        st.success("✅ Sampling completed. Preview below:")
        preview_cols = [column, 'probability'] if bin_col is None else [column, bin_col, 'probability']
        st.dataframe(sample_df[preview_cols].head())

        # Step 5: Download
        csv = sample_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Sampled Data", data=csv, file_name="sampled_data.csv", mime="text/csv")
