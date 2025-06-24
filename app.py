import streamlit as st
import pandas as pd

st.set_page_config(page_title="PPS Sampling with Binning", layout="centered")
st.title("📊 PPS Sampling with Binning")

uploaded_file = st.file_uploader("Upload your CSV file", type="csv")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        st.success("✅ File uploaded successfully.")
    except Exception as e:
        st.error(f"Failed to read file: {e}")
        st.stop()

    st.write("### Preview of Uploaded Data")
    st.dataframe(df.head())

    numeric_columns = df.select_dtypes(include='number').columns.tolist()
    if not numeric_columns:
        st.error("No numeric columns found in the dataset.")
        st.stop()

    column = st.selectbox("Select a numeric column for PPS sampling:", numeric_columns)

    if column:
        run_sampling = st.button("▶️ Run Sampling Setup")

        if run_sampling:
            mode = st.radio("Choose sampling mode:", ["Automatic (based on values)", "Custom binning"])

            if mode == "Automatic (based on values)":
                df = df[df[column].notnull() & (df[column] > 0)].copy()
                if df.empty:
                    st.error("No valid data found in selected column for automatic sampling.")
                    st.stop()
                df['probability'] = df[column] / df[column].sum()
                bin_col = None

            else:
                num_bins = st.number_input("Number of equal-frequency bins", min_value=2, step=1)
                labels_input = st.text_input("Enter labels for bins (comma-separated)", value="Low,Medium,High")
                labels = [l.strip() for l in labels_input.split(",") if l.strip()]
                if len(labels) != int(num_bins):
                    st.warning(f"Please enter exactly {int(num_bins)} labels.")
                    st.stop()

                try:
                    bin_col = f"{column}_qbin"
                    df[bin_col] = pd.qcut(df[column], q=int(num_bins), labels=labels)
                except Exception as e:
                    st.error(f"Error in binning: {e}")
                    st.stop()

                prob_input = st.text_input("Enter sampling weights for each bin (comma-separated)", value="0.3,0.4,0.3")
                try:
                    bin_weights = [float(w.strip()) for w in prob_input.split(",")]
                    if len(bin_weights) != int(num_bins):
                        st.warning(f"Expected {int(num_bins)} weights.")
                        st.stop()
                except Exception as e:
                    st.error(f"Invalid weights: {e}")
                    st.stop()

                prob_map = dict(zip(labels, bin_weights))
                df['probability'] = df[bin_col].map(prob_map).astype(float)
                total = df['probability'].sum()
                if total == 0 or pd.isna(total):
                    st.error("Total probability is zero or invalid.")
                    st.stop()
                df['probability'] = df['probability'] / total

            sample_size = st.number_input("Sample size", min_value=1, max_value=len(df), step=1)

            if st.button("📌 Sample Data"):
                try:
                    sample_df = df.sample(n=sample_size, weights='probability', random_state=42).reset_index(drop=True)
                    st.success("✅ Sampling completed.")
                    preview_cols = [column, 'probability'] if mode == "Automatic (based on values)" else [column, bin_col, 'probability']
                    st.dataframe(sample_df[preview_cols].head())

                    csv = sample_df.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download Sampled Data", data=csv, file_name="sampled_data.csv", mime="text/csv")
                except Exception as e:
                    st.error(f"Sampling failed: {e}")
else:
    st.info("👈 Please upload a CSV file to begin.")
