import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="MNCAH Surveillance Dashboard (2000-2005)",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Styling
st.markdown("""
    <style>
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    .stMetric {
        background-color: #f8f9fa;
        padding: 12px;
        border-radius: 8px;
        border-left: 4px solid #007bff;
    }
    </style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# DATA LOADING & PREPROCESSING
# -----------------------------------------------------------------------------
@st.cache_data
def load_data(file_path="datasets/mncah_data_2000_2025.csv"):
    df = pd.read_csv(file_path)
    
    # Filter out non-country metadata rows
    valid_countries = ['Kenya', 'Mali', 'Sierra Leone', 'Somalia']
    
    # Handle long-format datasets dynamically
    val_col = 'mncah_total' if 'mncah_total' in df.columns else 'value'
    df_clean = df[df['geographic_area'].isin(valid_countries)].copy()
    df_clean.rename(columns={val_col: 'Value', 'year': 'Year'}, inplace=True)

    # Data Cleaning
    df_clean['Year'] = pd.to_numeric(df_clean['Year'], errors='coerce')
    df_clean['Value'] = pd.to_numeric(df_clean['Value'], errors='coerce').fillna(0)
    df_clean.dropna(subset=['geographic_area', 'indicator', 'sex'], inplace=True)
    
    return df_clean

try:
    df_long = load_data("datasets/mncah_data_2000_2025.csv")
except FileNotFoundError:
    df_long = load_data("datasets/mncah_data_2000_2025.csv")

# -----------------------------------------------------------------------------
# SIDEBAR FILTERS
# -----------------------------------------------------------------------------
st.sidebar.title("🎛️ Navigation & Filters")

# 1. Geographic Area Filter
available_countries = sorted(df_long['geographic_area'].unique().tolist())
selected_countries = st.sidebar.multiselect(
    "🌍 Geographic Area:",
    options=available_countries,
    default=available_countries
)

# 2. Gender / Sex Filter
available_sex = sorted(df_long['sex'].unique().tolist())
selected_sex = st.sidebar.multiselect(
    "👤 Gender / Sex:",
    options=available_sex,
    default=['Total'] if 'Total' in available_sex else available_sex
)

# 3. Indicator Filter
available_indicators = sorted(df_long['indicator'].unique().tolist())
default_indicators = [available_indicators[0]] if available_indicators else []
selected_indicators = st.sidebar.multiselect(
    "📊 Health Indicators:",
    options=available_indicators,
    default=default_indicators
)

# 4. Year Range Slider
min_year = int(df_long['Year'].min())
max_year = int(df_long['Year'].max())
selected_years = st.sidebar.slider(
    "📅 Year Range:",
    min_value=min_year,
    max_value=max_year,
    value=(2005, max_year)
)

# 5. Data Threshold Option
exclude_zeros = st.sidebar.checkbox("Exclude Unreported / Zero Values", value=True)


# -----------------------------------------------------------------------------
# DATA FILTERING LOGIC
# -----------------------------------------------------------------------------
filtered_df = df_long[
    (df_long['geographic_area'].isin(selected_countries)) &
    (df_long['sex'].isin(selected_sex)) &
    (df_long['indicator'].isin(selected_indicators)) &
    (df_long['Year'] >= selected_years[0]) &
    (df_long['Year'] <= selected_years[1])
]

if exclude_zeros:
    filtered_df = filtered_df[filtered_df['Value'] > 0]


# -----------------------------------------------------------------------------
# MAIN HEADER & METRICS
# -----------------------------------------------------------------------------
st.title("🩺 Maternal, Newborn, Child & Adolescent Health (MNCAH) Dashboard")
st.markdown("Interactive analysis of key health indicators across **Kenya, Mali, Sierra Leone, and Somalia** (2000–2025).")

if filtered_df.empty:
    st.warning("⚠️ No data available matching the selected filter criteria. Please broaden your sidebar selections.")
    st.stop()

# Key KPI Summary Cards
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric(
        label="Selected Countries",
        value=f"{filtered_df['geographic_area'].nunique()} / {len(available_countries)}"
    )

with kpi2:
    st.metric(
        label="Active Indicators",
        value=f"{filtered_df['indicator'].nunique()}"
    )

with kpi3:
    avg_value = filtered_df['Value'].mean()
    st.metric(
        label="Average Value",
        value=f"{avg_value:.1f}"
    )

with kpi4:
    latest_reported_year = int(filtered_df['Year'].max())
    st.metric(
        label="Latest Reported Year",
        value=f"{latest_reported_year}"
    )

st.divider()


# -----------------------------------------------------------------------------
# VISUALIZATION TABS
# -----------------------------------------------------------------------------
tab_trend, tab_geo, tab_gender, tab_matrix, tab_data = st.tabs([
    "📈 Time Series",
    "📊 Country Comparison",
    "👥 Gender Disparity",
    "🔥 Completeness Heatmap",
    "📋 Data Table & Export"
])

# 1. TIME SERIES CHART
with tab_trend:
    st.subheader("Historical Indicator Trends")
    if len(selected_indicators) == 1:
        fig_trend = px.line(
            filtered_df,
            x='Year',
            y='Value',
            color='geographic_area',
            line_dash='sex',
            markers=True,
            title=f"Trend: {selected_indicators[0]}",
            labels={'Value': 'Percentage / Rate', 'geographic_area': 'Country'}
        )
    else:
        fig_trend = px.line(
            filtered_df,
            x='Year',
            y='Value',
            color='indicator',
            facet_col='geographic_area',
            facet_col_wrap=2,
            markers=True,
            title="Multi-Indicator Trends by Country"
        )
    fig_trend.update_layout(height=500, hovermode="x unified")
    st.plotly_chart(fig_trend, use_container_width=True)

# 2. COUNTRY COMPARISON BAR CHART
with tab_geo:
    st.subheader("Cross-Country Comparison")
    geo_agg = filtered_df.groupby(['geographic_area', 'indicator'], as_index=False)['Value'].mean()
    fig_bar = px.bar(
        geo_agg,
        x='geographic_area',
        y='Value',
        color='indicator',
        barmode='group',
        title="Average Indicator Values by Geographic Area",
        labels={'Value': 'Average Value', 'geographic_area': 'Country'}
    )
    fig_bar.update_layout(height=480)
    st.plotly_chart(fig_bar, use_container_width=True)

# 3. GENDER DISPARITY ANALYSIS
with tab_gender:
    st.subheader("Gender Disaggregation (Female vs. Male)")
    gender_df = df_long[
        (df_long['geographic_area'].isin(selected_countries)) &
        (df_long['sex'].isin(['Female', 'Male'])) &
        (df_long['indicator'].isin(selected_indicators)) &
        (df_long['Year'] >= selected_years[0]) &
        (df_long['Year'] <= selected_years[1])
    ]
    if exclude_zeros:
        gender_df = gender_df[gender_df['Value'] > 0]
        
    if gender_df.empty:
        st.info("No sex-disaggregated data (Female vs Male) available for the current indicator/country selection.")
    else:
        fig_gender = px.bar(
            gender_df,
            x='geographic_area',
            y='Value',
            color='sex',
            barmode='group',
            facet_col='indicator',
            facet_col_wrap=2,
            title="Female vs. Male Indicator Values Across Countries",
            color_discrete_map={'Female': '#e83e8c', 'Male': '#007bff'}
        )
        fig_gender.update_layout(height=480)
        st.plotly_chart(fig_gender, use_container_width=True)

# 4. REPORTING COMPLETENESS HEATMAP
with tab_matrix:
    st.subheader("Data Availability Matrix")
    heatmap_data = filtered_df.pivot_table(
        index='geographic_area',
        columns='Year',
        values='Value',
        aggfunc='mean'
    ).fillna(0)
    
    fig_heat = px.imshow(
        heatmap_data,
        labels=dict(x="Year", y="Country", color="Average Value"),
        x=heatmap_data.columns,
        y=heatmap_data.index,
        aspect="auto",
        color_continuous_scale="Viridis",
        title="Reporting Heatmap by Country and Year"
    )
    st.plotly_chart(fig_heat, use_container_width=True)

# 5. DATA TABLE & EXPORT
with tab_data:
    st.subheader("Filtered Data Records")
    st.dataframe(filtered_df, use_container_width=True)
    
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Filtered Data as CSV",
        data=csv,
        file_name="mncah_filtered_output.csv",
        mime="text/csv"
    )