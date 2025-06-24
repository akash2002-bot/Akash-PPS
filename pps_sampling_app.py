
import streamlit as st
import pandas as pd

st.set_page_config(page_title="PPS Sampling - Flexible Binning", layout="centered")
st.title("📊 PPS Sampling with Equal Width or Manual Binning")

# Initialize session state
for key in ["df", "sampling_started", "column", "mode", "bin_col", "sample_df"]:
    if key not in st.session_state:
        st.session_state[key] = None

# Step 1: File Upload
uploaded_file = st.file_uploader("Upload your CSV file", type="csv")
if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        st.session_state.df = df
        st.success("✅ File uploaded and read successfully.")
        st.write("### Preview of Uploaded Data")
        st.dataframe(df.head())
    except Exception as e:
        st.error(f"❌ File read failed: {e}")
        st.stop()

# Step 2: Select Numeric Column
if st.session_state.df is not None:
    numeric_columns = st.session_state.df.select_dtypes(include='number').columns.tolist()
    if not numeric_columns:
        st.error("No numeric columns found.")
        st.stop()

    st.session_state.column = st.selectbox("Select a numeric column for PPS sampling:", numeric_columns)

    if st.button("▶️ Run Sampling Setup"):
        st.session_state.sampling_started = True

# Step 3: Sampling Setup
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
        # Step 1: Number of bins
        num_bins = st.number_input("Step 1: Number of bins", min_value=2, value=3, step=1)

        # Step 2: Binning method
        binning_mode = st.radio("Step 2: Define bin ranges", ["Automatic", "Manual"])

        try:
            if binning_mode == "Automatic":
                bin_col = f"{column}_cut"
                df[bin_col] = pd.cut(df[column], bins=int(num_bins))
                unique_bins = df[bin_col].cat.categories.astype(str).tolist()
            else:
                min_val = float(df[column].min())
                max_val = float(df[column].max())
                st.markdown(f"ℹ️ Column range: {min_val:.2f} – {max_val:.2f}")
                manual_bins_input = st.text_input(
                    f"Enter {num_bins - 1} internal cutoff points (comma-separated):",
                    placeholder="e.g., 30, 60"
                )
                cutoffs = [float(x.strip()) for x in manual_bins_input.split(",")]
                if len(cutoffs) != num_bins - 1:
                    st.warning(f"⚠️ You must provide exactly {num_bins - 1} breakpoints.")
                    st.stop()

                all_bins = [min_val] + cutoffs + [max_val + 0.01]
                bin_col = f"{column}_cut"
                df[bin_col] = pd.cut(df[column], bins=all_bins, include_lowest=True)
                unique_bins = df[bin_col].cat.categories.astype(str).tolist()

            st.session_state.bin_col = bin_col

            # Step 3: Show bin ranges
            st.markdown("### Bin Ranges (Generated):")
            bin_ranges_df = pd.DataFrame({
                "Bin Number": list(range(1, len(unique_bins)+1)),
                "Range": unique_bins
            })
            st.table(bin_ranges_df)

            # Step 4: Label bins
            st.markdown("Step 3: Label your bins")
            default_labels = ",".join([f"Bin{i+1}" for i in range(len(unique_bins))])
            user_labels_input = st.text_input(f"Enter {len(unique_bins)} labels (comma-separated)", value=default_labels)
            user_labels = [label.strip() for label in user_labels_input.split(",")]
            if len(user_labels) != len(unique_bins):
                st.warning(f"Please enter exactly {len(unique_bins)} labels.")
                st.stop()

            # Assign custom labels
            bin_label_map = dict(zip(unique_bins, user_labels))
            df['bin_label'] = df[bin_col].astype(str).map(bin_label_map)

            # Step 5: Weights
            st.markdown("Step 4: Assign weights to each bin")
            default_weights = ",".join(["1.0"] * len(user_labels))
            prob_input = st.text_input("Enter weights (comma-separated)", value=default_weights)
            bin_weights = [float(w.strip()) for w in prob_input.split(",")]
            if len(bin_weights) != len(user_labels):
                st.warning(f"Expected {len(user_labels)} weights.")
                st.stop()

            prob_map = dict(zip(user_labels, bin_weights))
            df['probability'] = df['bin_label'].map(prob_map).astype(float)
            total = df['probability'].sum()
            if total == 0 or pd.isna(total):
                st.error("Total probability is zero or invalid.")
                st.stop()
            df['probability'] = df['probability'] / total
            st.session_state.sample_ready_df = df

        except Exception as e:
            st.error(f"Error in binning or labeling: {e}")
            st.stop()

    # Step 6: Sampling
    sample_size = st.number_input("Step 5: Enter sample size", min_value=1, max_value=len(st.session_state.sample_ready_df), step=1)

    if st.button("📌 Step 6: Sample Data"):
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

# Step 7: Show and Download Sample
if st.session_state.sample_df is not None:
    st.subheader("🎯 Sampled Data Preview")
    preview_cols = [st.session_state.column, 'probability']
    if st.session_state.bin_col:
        preview_cols.insert(1, st.session_state.bin_col)
    st.dataframe(st.session_state.sample_df[preview_cols].head())

    csv = st.session_state.sample_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Sampled Data", data=csv, file_name="sampled_data.csv", mime="text/csv")
