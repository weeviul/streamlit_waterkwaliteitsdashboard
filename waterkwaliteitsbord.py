import io
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Waterkwaliteitsdashboard", layout="wide")
st.title("Waterkwaliteitsdashboard")

# --- Sidebar opties ---
st.sidebar.header("Instellingen")
decimal = st.sidebar.selectbox("Decimaalteken", options=[",", "."], index=1)
delimiter = st.sidebar.selectbox("Scheidingsteken", options=[",", ";", "\t", "|", "auto"], index=4)
dayfirst = st.sidebar.checkbox("Datum is dag-eerst (EU-formaat)", value=True)
resample_optie = st.sidebar.selectbox("Resampling", ["Geen", "5min", "15min", "1H", "6H", "1D"], index=0)
rolling_window = st.sidebar.number_input("Moving average (aantal punten)", min_value=0, value=0, step=1)

uploaded_file = st.file_uploader("Laad een CSV-bestand op", type=["csv"])

@st.cache_data(show_spinner=False)
def _read_csv(file, delimiter, decimal, dayfirst):
    # delimiter autodetect
    sep = None if delimiter == "auto" else delimiter
    # pandas kan ',' als decimaalteken aan met decimal=','
    df = pd.read_csv(file, sep=sep, engine="python", decimal=decimal)
    # normalize kolomnamen
    df.columns = [c.strip() for c in df.columns]
    # zoek tijdkolom varianten
    tijd_col_candidates = [c for c in df.columns if c.lower() in ["tijd", "time", "timestamp", "datetime"]]
    if not tijd_col_candidates:
        return None, "Geen tijdkolom gevonden (verwacht: 'tijd', 'time', 'timestamp', 'datetime')."
    tijd_col = tijd_col_candidates[0]
    df[tijd_col] = pd.to_datetime(df[tijd_col], errors="coerce", dayfirst=dayfirst)
    df = df.dropna(subset=[tijd_col]).sort_values(tijd_col)
    df = df.set_index(tijd_col)
    return df, None

if uploaded_file is not None:
    df, err = _read_csv(uploaded_file, delimiter, decimal, dayfirst)
    if err:
        st.error(err)
    else:
        # numerieke kolommen kiezen
        num_cols = df.select_dtypes(include="number").columns.tolist()
        if not num_cols:
            st.warning("Geen numerieke kolommen gevonden om te plotten.")
        else:
            st.dataframe(df.head(50))

            # parameters selecteren
            geselecteerde_parameters = st.multiselect(
                "Kies parameters", num_cols, default=num_cols[: min(3, len(num_cols))]
            )

            # optioneel resamplen (gemiddelde)
            plot_df = df.copy()
            if resample_optie != "Geen":
                plot_df = plot_df.resample(resample_optie).mean().dropna(how="all")

            # optioneel moving average
            if rolling_window and rolling_window > 0:
                plot_df = plot_df.rolling(rolling_window, min_periods=1).mean()

            if geselecteerde_parameters:
                fig, ax = plt.subplots(figsize=(11, 5))
                for parameter in geselecteerde_parameters:
                    ax.plot(plot_df.index, plot_df[parameter], label=parameter)

                ax.set_xlabel("Tijd")
                ax.set_ylabel("Waarde")
                ax.set_title("Tijdsgrafiek van geselecteerde parameters")
                ax.legend()
                ax.grid(True)
                plt.xticks(rotation=45)
                plt.tight_layout()
                st.pyplot(fig)

                # download van gefilterde data
                buffer = io.StringIO()
                plot_df[geselecteerde_parameters].to_csv(buffer)
                st.download_button(
                    "Download gefilterde data (CSV)",
                    data=buffer.getvalue(),
                    file_name="gefilterde_data.csv",
                    mime="text/csv",
                )
            else:
                st.info("Selecteer minstens één parameter om een grafiek te tonen.")
else:
    st.info("Laad een CSV op om te starten.")
