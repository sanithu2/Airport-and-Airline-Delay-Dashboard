import pandas as pd
import duckdb
import plotly.express as px
import streamlit as st

df = pd.read_csv('Airline_Delay_Cause_Extended.csv')
airport_coordinates_df = pd.read_csv('airport_coordinates.csv')

@st.cache_data
def unique_carriers():
    """
        Returns a LIST of all the unique carriers in the database.
    """
    with duckdb.connect() as con:
        con.register("df", df)
    carrier_list = [
        row[0] for row in duckdb.sql("""
        SELECT DISTINCT carrier_name
        FROM df
        ORDER BY carrier_name
    """).fetchall()
    ]

    return carrier_list

def unique_airports_for_carrier(carrier_name):
    """
        Returns a LIST of the unique airports for a specific carrier in the database.
        The input carrier_name is the name of the specific carrier.
    """
    with duckdb.connect() as con:
        con.register("df", df)

    carrier_rows = duckdb.sql("""
        SELECT *
        FROM df
        WHERE carrier_name = ?
    """, params = [carrier_name]).df()

    airport_list = [
        row[0] for row in duckdb.sql("""
        SELECT DISTINCT airport_name
        FROM carrier_rows
        ORDER BY airport_name
    """).fetchall()
    ]

    return airport_list

def filter_database(airline, airport = None, year = None, month = None):
    querry = f"""
        SELECT * 
        FROM df
        WHERE carrier_name = '{airline}'
    """ 

    f=""

    if airport is not None:
        f += f"AND airport_name = '{airport}'"               

    if year is not None:
        f += f"AND year = {year}"

    if month is not None:
        f += f"AND month = {month}"

    querry += f

    filtered_df = duckdb.sql(querry).df()

    return filtered_df

def summary(airline, airport = None, year = None, month = None):
    filtered_df = filter_database(airline, airport, year, month)

    total_flights = filtered_df['arr_flights'].sum()

    if total_flights == 0:
        return None
    
    delayed_flights = filtered_df['arr_del15'].sum()
    proportion_delayed = delayed_flights/total_flights

    return total_flights, delayed_flights, proportion_delayed

def causes_and_numbers(airline, airport = None, year = None, month = None):
    filtered_df = filter_database(airline, airport, year, month)

    dictionary = {'Airline': 0, 'Weather': 0, 'National Aviation System': 0, 'Late Arriving Aircraft': 0, 'Security': 0}

    dictionary['Airline'] = filtered_df['carrier_ct'].sum()
    dictionary['Weather'] = filtered_df['weather_ct'].sum()
    dictionary['National Aviation System'] = filtered_df['nas_ct'].sum()
    dictionary['Late Arriving Aircraft'] = filtered_df['late_aircraft_ct'].sum()
    dictionary['Security'] = filtered_df['security_ct'].sum()

    causes_and_number_df = pd.DataFrame(list(dictionary.items()), columns = ["Category", "Number"])

    return causes_and_number_df

def delay_cause_chart(airline, airport = None, year = None, month = None):
    data = causes_and_numbers(airline, airport, year, month)
    return px.pie(data, names = "Category", values = "Number", hole = 0.45, title = "Delay Causes")

def get_month(month_num):
    month = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'July', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    return month[month_num-1]

def filter_database_airport_fixed(airport, airline = None, year = None, month = None):
    querry = f"""
        SELECT * 
        FROM df
        WHERE airport = '{airport}'
    """ 

    f=""

    if airline is not None:
        f += f"AND carrier_name = '{airline}'"

    if year is not None:
        f += f"AND year = {year}"

    if month is not None:
        f += f"AND month = {month}"

    querry += f

    filtered_df = duckdb.sql(querry).df()

    return filtered_df


def airport_summary_for_year(year, carrier_name = None):
    if carrier_name is None:
        airport_table = duckdb.sql("""
            SELECT 
                airport,
                airport_name,
                SUM(arr_del15) as total_delayed, 
                SUM(arr_flights) AS total_arrivals, 
                SUM(arr_del15) / NULLIF(SUM(arr_flights), 0) AS proportion_delayed,
                ROUND((SUM(arr_del15) / NULLIF(SUM(arr_flights), 0))*100,1) AS percentage_delayed
            FROM df
            WHERE YEAR = ?
            GROUP BY airport, airport_name
        """, params = [year]).df()
    else:
        airport_table = duckdb.sql("""
            SELECT 
                airport,
                airport_name,
                SUM(arr_del15) as total_delayed, 
                SUM(arr_flights) AS total_arrivals, 
                SUM(arr_del15) / NULLIF(SUM(arr_flights), 0) AS proportion_delayed,
                ROUND((SUM(arr_del15) / NULLIF(SUM(arr_flights), 0))*100,1) AS percentage_delayed
            FROM df
            WHERE YEAR = ? AND carrier_name = ?
            GROUP BY airport, airport_name
        """, params = [year, carrier_name]).df()

    table_with_coordinates = duckdb.sql("""
        SELECT 
            t.airport,
            t.airport_name,
            t.total_delayed,
            t.total_arrivals,
            t.proportion_delayed,
            t.percentage_delayed,
            c.latitude,
            c.longitude
        FROM airport_table as t
        LEFT JOIN airport_coordinates_df as c
            ON t.airport = c.airport
    """).df()

    ranked_airports = duckdb.sql("""
        SELECT *
        FROM table_with_coordinates
        ORDER BY total_delayed DESC
    """).df()

    return ranked_airports

def seasonal_filter_database(year, season, month = None, carrier_name = None):
    querry = """
        SELECT *
        FROM df
        WHERE 
    """

    f = ''

    match season:
        case "All":
            f += f"year = {year}"
        case "Winter":
            f += f"(year = {year - 1} AND month = 12) OR (year = {year} AND month BETWEEN 1 AND 2)"
        case "Spring":
            f += f"(year = {year} AND month BETWEEN 3 AND 5)"
        case "Summer":
            f += f"(year = {year} AND month BETWEEN 6 AND 8)"
        case "Fall":
            f += f"(year = {year} AND month BETWEEN 9 AND 11)"

        
    if month is not None:
        f+= f"AND month = {month}"

    if carrier_name is not None:
        f += f" AND carrier_name = '{carrier_name}'"

    querry += f

    seasonal_filtered_database = duckdb.sql(querry).df()

    return seasonal_filtered_database

def seasonal_airport_summary(year, season, month = None, carrier_name = None):
    filtered_database = seasonal_filter_database(year, season, month, carrier_name)

    airport_table = duckdb.sql("""
        SELECT 
            airport,
            airport_name,
            SUM(arr_del15) as total_delayed, 
            SUM(arr_flights) AS total_arrivals, 
            SUM(arr_del15) / NULLIF(SUM(arr_flights), 0) AS proportion_delayed,
            ROUND((SUM(arr_del15) / NULLIF(SUM(arr_flights), 0))*100,1) AS percentage_delayed
        FROM filtered_database
        GROUP BY airport, airport_name
    """).df()

    table_with_coordinates = duckdb.sql("""
        SELECT 
            t.airport,
            t.airport_name,
            t.total_delayed,
            t.total_arrivals,
            t.proportion_delayed,
            t.percentage_delayed,
            c.latitude,
            c.longitude
        FROM airport_table as t
        LEFT JOIN airport_coordinates_df as c
            ON t.airport = c.airport
    """).df()
    
    ranked_airports = duckdb.sql("""
        SELECT *
        FROM table_with_coordinates
        ORDER BY total_delayed DESC
    """).df()
    
    return ranked_airports