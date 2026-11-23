import streamlit as st
import folium
from helpers import *
import folium
import streamlit.components.v1 as components
from branca.element import Element

#Airline and Airport Delay Map
st.title("Airline and Airport Delays")

with st.sidebar:
    airline = st.selectbox("Airline", unique_carriers())
    view = st.radio("View", ["Monthly airline summary" ,"Annual airline summary", "Monthly by airport"])
    year = st.number_input("Year", min_value = 2013, max_value = 2026, value=2026, step=1)
    airport = None
    month = None
    if view == "Monthly by airport":
        month = st.number_input("Month", min_value = 1, max_value = 12, step=1)
        airport = st.selectbox("Airport", unique_airports_for_carrier(airline))
    elif view == "Monthly airline summary":
        month = st.number_input("Month", min_value = 1, max_value = 12, step = 1)
        airport = None

map_scope = st.radio("Map Airlines", ["All Airlines", "Selected Airline"], horizontal = True)

if map_scope == "All Airlines":
    st.subheader(f"Airport Delays in {year}")
    airports = airport_summary_for_year(year)
else:
    st.subheader(f"Airport Delays in {year} for {airline}")
    airports = airport_summary_for_year(year, airline)

airport_map = folium.Map(
    location = [39, -98],
    zoom_start = 4,
    tiles = "OpenStreetMap",
)

max_delayed = airports["total_delayed"].max()

for row in airports.itertuples(index = False):
    radius = 3,
    if max_delayed > 0:
        radius = max(3, 25 * (row.total_delayed/max_delayed) ** 0.5)

    folium.CircleMarker(
        location = [row.latitude, row.longitude],
        radius = radius,
        color = "white",
        weight = 1,
        fill = True,
        fill_color = '#DE6736',
        fill_opacity = 0.75,
        tooltip=(f"Airport: {row.airport}<br>"
                 f"Total flights; {row.total_arrivals:.0f}<br>"
                 f"Total delayed flights: {row.total_delayed:.0f}<br>"
                 f"Percentage delayed: {row.proportion_delayed:.1%}"
                 )
    ).add_to(airport_map)

components.html(airport_map.get_root().render(), height = 520)


st.subheader(f"Airports ranked by delayed arrivals in {year}")

st.dataframe(
    airports[["airport", "airport_name", "total_delayed","percentage_delayed"]],
    column_config={
        "airport": "Airport Code",
        "airport_name": "Airport Name",
        "total_delayed": "Total Delayed Flights",
        "percentage_delayed": "Percentage Delayed"
    },
    hide_index = True
)

#Time of Year Map
st.subheader(f"Airport Delays by Time of Year")
time_period = st.radio("Time Period", ["Monthly", "Seasonal"], horizontal = True)
airline_selection = st.radio("Airlines", ["All Airlines", "Selected Airline"], horizontal = True)

match time_period:
    case "Monthly":
        month_seasonal = st.slider("Select month", min_value = 1, max_value = 12, step = 1)
        match airline_selection:
            case "All Airlines":
                airports_seasonal = seasonal_airport_summary(year, "All", month = month_seasonal)
            case "Selected Airline":
                airports_seasonal = seasonal_airport_summary(year, "All", month = month_seasonal, carrier_name= airline)
    case "Seasonal":
        season = st.selectbox("Season", ["Spring", "Summer", "Fall", "Winter"])
        match airline_selection:
            case "All Airlines":
                airports_seasonal = seasonal_airport_summary(year, season)
            case "Selected Airline":
                airports_seasonal = seasonal_airport_summary(year, season, carrier_name= airline)

airports_seasonal_map = folium.Map(
    location = [39, -98],
    zoom_start = 4,
    tiles = "OpenStreetMap"
)

min_radius = 6
max_radius = 30
max_seasonal_delayed = airports_seasonal["total_delayed"].max()

legend_html = """
<div style="
    position: fixed;
    bottom: 15px;
    left: 10px;
    z-index: 1000;
    background: white;
    padding: 12px 15px;
    border-radius: 6px;
    box-shadow: 0 1px 5px rgba(0, 0, 0, 0.25);
    font: 14px/1.5 Arial, sans-serif;
    color: black;
">
    <strong>Airport Delay Rate</strong>
    <div><span style="color: green;">●</span> Under 15%</div>
    <div><span style="color: orange;">●</span> 15% to under 25%</div>
    <div><span style="color: red;">●</span> 25% or higher</div>
    <div style="margin-top: 12px;">Circle size = delayed flights</div>
</div>
"""

for row in airports_seasonal.itertuples(index = False):
    radius = min_radius
    if max_seasonal_delayed > 0:
        share_of_max = row.total_delayed / max_seasonal_delayed
        radius = min_radius + (max_radius - min_radius) * share_of_max ** 0.5

    if row.percentage_delayed >= 25:
        color = "#DE6736"
    elif (row.percentage_delayed >= 15 and row.percentage_delayed <=25):
        color = "#E6B90D"
    else:
        color = "#7BBC53"

    folium.CircleMarker(
        location = [row.latitude, row.longitude],
        radius = radius,
        color = "white",
        weight = 1,
        fill = True,
        fill_color = color,
        fill_opacity = 0.65,
        tooltip = (
            f"Airport: {row.airport}<br>"
            f"Total flights: {row.total_arrivals}<br>"
            f"Total delayed arrivals: {row.total_delayed}<br>"
            f"Percentage delayed: {row.proportion_delayed:.1%}"
        )
    ).add_to(airports_seasonal_map)

airports_seasonal_map.get_root().html.add_child(Element(legend_html))
components.html(airports_seasonal_map.get_root().render(), height=520)

#Container showing quick statistics
with st.container(border = True):
    if view == "Monthly by airport":
        st.write(f"Monthly airline delays for the month of {get_month(month)} arriving at {airport}")
    elif view == "Monthly airline summary":
        st.write(f"Monthly airline delays across all airports for the month of {get_month(month)}")
    elif view == "Annual airline summary":
        st.write(f"Annual airline summary across all airlines for the year {year}")

    result = summary(airline, airport, year, month)

    if result is None:
        st.warning("No data available")
    else:
        total_flights, delayed_flights, proportion_delayed = result
        col1, col2 = st.columns(2)

        with col1:
            st.metric('Total Flights', f"{int(total_flights):,}")
        with col2:
            st.metric('Delayed Flights', f"{int(delayed_flights):,}")

        st.write(f"Percentage of flights delayed ≥ 15 minutes: {proportion_delayed*100:.2f}%")

        st.progress(proportion_delayed)

    st.subheader('Delay Causes')
    delay_causes_df = causes_and_numbers(airline, airport, month, year)

    figure = delay_cause_chart(airline, airport, year, month)

    st.plotly_chart(figure, theme="streamlit")