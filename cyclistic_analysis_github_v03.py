# -*- coding: utf-8 -*-
"""
Created on Wed Aug 12 18:16:05 2026

@author: angus
"""

#Imports, Streamlit config

import pandas as pd
import streamlit as st
import plotly.io as pio
import plotly.express as px
import plotly.graph_objects as go
import requests
from io import BytesIO
from zipfile import ZipFile

st.set_page_config(layout="wide")

# Read monthly csv files and combine into one dataframe.
data_urls = [
    "https://divvy-tripdata.s3.amazonaws.com/202509-divvy-tripdata.zip",
    "https://divvy-tripdata.s3.amazonaws.com/202510-divvy-tripdata.zip",
    "https://divvy-tripdata.s3.amazonaws.com/202511-divvy-tripdata.zip",
    "https://divvy-tripdata.s3.amazonaws.com/202512-divvy-tripdata.zip",
    "https://divvy-tripdata.s3.amazonaws.com/202601-divvy-tripdata.zip",
    "https://divvy-tripdata.s3.amazonaws.com/202602-divvy-tripdata.zip",
    "https://divvy-tripdata.s3.amazonaws.com/202603-divvy-tripdata.zip",
    "https://divvy-tripdata.s3.amazonaws.com/202604-divvy-tripdata.zip",
    "https://divvy-tripdata.s3.amazonaws.com/202605-divvy-tripdata.zip",
    "https://divvy-tripdata.s3.amazonaws.com/202606-divvy-tripdata.zip",
    "https://divvy-tripdata.s3.amazonaws.com/202607-divvy-tripdata.zip",
    "https://divvy-tripdata.s3.amazonaws.com/202608-divvy-tripdata.zip",
]


def create_analysis_tables():
    
    # Running totals for the summary tables
    hourly_totals = {}
    daily_totals = {}
    monthly_totals = {}
    ridetype_totals = {}

    # For average ride length we need total seconds AND ride count.
    # We combine these across months at the end so the final
    # average is correctly weighted by number of rides.
    ride_time_totals = {}

    # Geographic totals
    geo_totals = {}

    # The 35 duplicate rides identified in the original code.
    # April IDs are retained only until May has been processed.
    april_30_ids = set()

    for url in data_urls:

        response = requests.get(url)
        response.raise_for_status()

        with ZipFile(BytesIO(response.content)) as z:

            csv_file = [
                file for file in z.namelist()
                if file.endswith(".csv")
            ][0]

            # Only load columns actually required for analysis.
            new_df = pd.read_csv(
                z.open(csv_file),
                usecols=[
                    "ride_id",
                    "rideable_type",
                    "started_at",
                    "ended_at",
                    "end_station_name",
                    "member_casual",
                    "start_lat",
                    "start_lng"
                ]
            )

        # Remove the known April/May duplicate rides
        if "202604" in url:

            april_30_ids = set(
                new_df.loc[
                    new_df["started_at"].str.startswith("2026-04-30"),
                    "ride_id"
                ]
            )

        elif "202605" in url:

            new_df = new_df[
                ~new_df["ride_id"].isin(april_30_ids)
            ].copy()

        # Data cleaning

        new_df["started_at"] = pd.to_datetime(new_df["started_at"])
        new_df["ended_at"] = pd.to_datetime(new_df["ended_at"])

        # Filter out classic bike rides that were automatically
        # ended after 25 hours because the bike was abandoned.
        new_df = new_df[
            (new_df["rideable_type"] != "classic_bike")
            | new_df["end_station_name"].notna()
        ].copy()

        # end_station_name is no longer required.
        new_df.drop(
            columns="end_station_name",
            inplace=True
        )

        # Add analysis columns.
        new_df["day_of_week"] = new_df["started_at"].dt.day_name()
        new_df["month"] = new_df["started_at"].dt.month_name()
        new_df["start_hour"] = new_df["started_at"].dt.hour

        new_df["ride_length (seconds)"] = (
            (new_df["ended_at"] - new_df["started_at"])
            .dt.total_seconds()
            .round()
            .astype("int32")
        )

        # Convert repeated string values to categorical.
        new_df["member_casual"] = (
            new_df["member_casual"].astype("category")
        )

        new_df["rideable_type"] = (
            new_df["rideable_type"].astype("category")
        )

        # Set month/day order

        month_order = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December"
        ]

        day_order = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday"
        ]

        new_df["month"] = pd.Categorical(
            new_df["month"],
            categories=month_order,
            ordered=True
        )

        new_df["day_of_week"] = pd.Categorical(
            new_df["day_of_week"],
            categories=day_order,
            ordered=True
        )

        # Users by hour

        monthly_hourly = (
            new_df
            .groupby(
                ["start_hour", "member_casual"],
                observed=True
            )
            .size()
        )

        for key, value in monthly_hourly.items():
            hourly_totals[key] = (
                hourly_totals.get(key, 0) + value
            )

        # Users by day

        monthly_daily = (
            new_df
            .groupby(
                ["day_of_week", "member_casual"],
                observed=True
            )
            .size()
        )

        for key, value in monthly_daily.items():
            daily_totals[key] = (
                daily_totals.get(key, 0) + value
            )


        # Users by month

        monthly_monthly = (
            new_df
            .groupby(
                ["month", "member_casual"],
                observed=True
            )
            .size()
        )

        for key, value in monthly_monthly.items():
            monthly_totals[key] = (
                monthly_totals.get(key, 0) + value
            )


        # Users by ride type

        monthly_ridetype = (
            new_df
            .groupby(
                ["rideable_type", "member_casual"],
                observed=True
            )
            .size()
        )

        for key, value in monthly_ridetype.items():
            ridetype_totals[key] = (
                ridetype_totals.get(key, 0) + value
            )


        # Average ride length
        #
        # Store SUM and COUNT rather than monthly averages.
        # This means the final average is correctly weighted.
        #

        monthly_ride_time = (
            new_df
            .groupby(
                ["day_of_week", "member_casual"],
                observed=True
            )["ride_length (seconds)"]
            .agg(["sum", "count"])
        )

        for key, row in monthly_ride_time.iterrows():

            if key not in ride_time_totals:
                ride_time_totals[key] = {
                    "sum": 0,
                    "count": 0
                }

            ride_time_totals[key]["sum"] += row["sum"]
            ride_time_totals[key]["count"] += row["count"]


        # Geographic data

        new_df["lat_bin"] = new_df["start_lat"].round(4)
        new_df["lng_bin"] = new_df["start_lng"].round(4)

        monthly_geo = (
            new_df
            .groupby(
                [
                    "lat_bin",
                    "lng_bin",
                    "member_casual"
                ],
                observed=True
            )
            .size()
        )

        for key, value in monthly_geo.items():
            geo_totals[key] = (
                geo_totals.get(key, 0) + value
            )


        # IMPORTANT:
        # The monthly dataframe is no longer needed.


        del new_df
        del response


    # Convert running totals into the exact tables expected by
    # the existing visualisation code.

    # Users by hour
    
    users_by_hour = (
        pd.Series(hourly_totals, name="count")
        .rename_axis(
            ["start_hour", "member_casual"]
        )
        .unstack(fill_value=0)
    )

    users_by_hour = users_by_hour.reindex(
        columns=["casual", "member"],
        fill_value=0
    )


    # Users by day

    users_by_day = (
        pd.Series(daily_totals, name="count")
        .rename_axis(
            ["day_of_week", "member_casual"]
        )
        .unstack(fill_value=0)
    )

    users_by_day = users_by_day.reindex(
        index=day_order
    )

    users_by_day = users_by_day.reindex(
        columns=["casual", "member"],
        fill_value=0
    )


    # Users by month

    users_by_month = (
        pd.Series(monthly_totals, name="count")
        .rename_axis(
            ["month", "member_casual"]
        )
        .unstack(fill_value=0)
    )

    users_by_month = users_by_month.reindex(
        index=month_order
    )

    users_by_month = users_by_month.reindex(
        columns=["casual", "member"],
        fill_value=0
    )


    # Users by ride type

    users_by_ridetype = (
        pd.Series(ridetype_totals, name="count")
        .rename_axis(
            ["rideable_type", "member_casual"]
        )
        .unstack(fill_value=0)
    )

    users_by_ridetype = users_by_ridetype.reindex(
        columns=["casual", "member"],
        fill_value=0
    )

    users_by_ridetype["casual_pct"] = (
        users_by_ridetype["casual"]
        / users_by_ridetype["casual"].sum()
        * 100
    )

    users_by_ridetype["member_pct"] = (
        users_by_ridetype["member"]
        / users_by_ridetype["member"].sum()
        * 100
    )


    # Average ride time

    avg_seconds_data = {}

    for key, values in ride_time_totals.items():

        avg_seconds_data[key] = (
            values["sum"] / values["count"]
        )

    avg_seconds = (
        pd.Series(avg_seconds_data, name="average_seconds")
        .rename_axis(
            ["day_of_week", "member_casual"]
        )
        .unstack()
    )

    avg_seconds = avg_seconds.reindex(
        index=day_order
    )

    avg_seconds = avg_seconds.reindex(
        columns=["casual", "member"]
    )

    avg_minutes = avg_seconds / 60


    # Geographic data

    geo_data = (
        pd.Series(geo_totals, name="count")
        .rename_axis(
            ["lat_bin", "lng_bin", "member_casual"]
        )
        .unstack(fill_value=0)
        .reset_index()
    )

    geo_data = geo_data.reindex(
        columns=[
            "lat_bin",
            "lng_bin",
            "casual",
            "member"
        ],
        fill_value=0
    )



    # Total rides

    total_rides = pd.DataFrame({
        "member_casual": ["casual", "member"],
        "rides": [
            users_by_hour["casual"].sum(),
            users_by_hour["member"].sum()
        ]
    })


    return (
        users_by_hour,
        users_by_day,
        users_by_month,
        users_by_ridetype,
        avg_minutes,
        geo_data,
        total_rides
    )


# Run the processing
(
    users_by_hour,
    users_by_day,
    users_by_month,
    users_by_ridetype,
    avg_minutes,
    geo_data,
    total_rides
) = create_analysis_tables()

st.write("Data processing complete")

#st.write(
#    f"Memory usage: "
#    f"{df_cleaned.memory_usage(deep=True).sum() / 1024**3:.2f} GB"
#)

#memory_usage = (
#    df_cleaned.memory_usage(deep=True)
#    .sort_values(ascending=False)
#)

#st.write(
#    (memory_usage / 1024**2).round(1)
#)

# Visualizations

# Define colour scheme

color_map = {
    "casual": "#f1fb67",
    "member": "#4095a5"
    }

# Total number of rides per user type.

fig_total_rides = px.pie(
    total_rides,
    names="member_casual",
    values="rides",
    color="member_casual",
    color_discrete_map=color_map,
    title="Total Number of Rides per User Type",
    labels={
        "casual": "Casual Users",
        "member": "Members",
        "rides": "Total Trips"
    },
)

fig_total_rides.update_traces(
    hovertemplate=(
        "<b>User Type:</b> %{label}<br>"
        "<b>Total Trips:</b> %{value}<br>"
        "<b>Share:</b> %{percent}"
    )
)

# Numbers of rides per day of the week by user type.

fig_users_by_day = px.bar(
    users_by_day.reset_index(),
    x="day_of_week",
    y=["casual", "member"],
    barmode = "group",
    title="Number of Rides per Day by User Type",
    labels = {
        "day_of_week": "Day of the Week",
        "value": "Number of Rides",
        "variable": "User Type"
    },
    color_discrete_map = color_map
)

fig_users_by_day.update_traces(hovertemplate = "No. of rides: %{y}<extra></extra>")

# Number of rides per month by user type

fig_users_by_month = px.bar(
    users_by_month.reset_index(),
    x="month",
    y=["casual", "member"],
    barmode = "group",
    title="Number of Rides per Month by User Type",
    labels = {
        "month": "Month",
        "value": "Number of Rides",
        "variable": "User Type"
    },
    color_discrete_map= color_map
)

fig_users_by_month.update_traces(hovertemplate = "No. of rides: %{y}<extra></extra>")

#Length of ride per day of the week by user type.

fig_ride_time_by_day = px.bar(
    avg_minutes.reset_index(),
    x= "day_of_week",
    y=["casual", "member"],
    barmode="group",
    title = "Average Ride Time per Day of the Week by User Type",
    labels = {
        "day_of_week": "Day of the Week",
        "value": "Average Ride Time (Minutes)",
        "variable": "User Type"
    },
    color_discrete_map= color_map
)

fig_ride_time_by_day.update_traces(hovertemplate = "Ride length: %{y:.2f} mins<extra></extra>")


fig_rides_by_hour = px.line(
    users_by_hour.reset_index(),
    x = "start_hour",
    y = ["casual", "member"],
    markers = True,
    labels = {
        "start_hour": "Time of Day",
        "value": "Number of Rides",
        "variable": "User Type"
    },
    title = "Total Number of Rides per Hour by User Type",
    color_discrete_map= color_map
    )

fig_rides_by_hour.update_traces(
    hovertemplate="<b>%{fullData.name}</b><br>Number of Rides = %{y:,}<extra></extra>"
)

fig_rides_by_hour.update_layout(hovermode = "x unified",
    xaxis = dict(
        unifiedhovertitle = dict(
            text = "<b>Hour: %{x}:00</b>"
            )
        )
    )


# Number of rides per ride type by user type

fig_users_by_ridetype = px.bar(
    users_by_ridetype.reset_index(),
    x="rideable_type",
    y=["casual_pct", "member_pct"],
    barmode = "group",
    title="Users per type of bicycle (%)",
    labels = {
        "rideable_type": "Type of Bicycle",
        "value": "Percentage of total usage",
        "variable": "User Type",
        "casual_pct": "casual",
        "member_pct": "member"
    },
    color_discrete_map = {
        "casual_pct": "#f1fb67",
        "member_pct": "#4095a5"}
    )

fig_users_by_ridetype.update_traces(hovertemplate = "Percentage of Users: %{y:.1f}%<extra></extra>")


#Overlay geographic ride data over a map of Chicago

max_rides = max(
    geo_data["casual"].max(),
    geo_data["member"].max()
)

# Shared colour range
color_min = 0
color_max = max_rides

# Shared marker size
max_marker_size = 25

sizeref = 2.0 * max_rides / (max_marker_size ** 2)

chicago_map = go.Figure()

# Casual rides

chicago_map.add_trace(
    go.Scattermap(
        lat=geo_data["lat_bin"],
        lon=geo_data["lng_bin"],
        mode="markers",
        marker=dict(
            size=geo_data["casual"],
            color=geo_data["casual"],
            colorscale="BlueRed",
            cmin=color_min,
            cmax=color_max,
            sizemode="area",
            sizeref=sizeref,
            opacity=0.7,
            showscale=True
        ),
        name="Casuals",
        customdata=geo_data[["casual", "member"]].values,
        hovertemplate=(
            "<b>Casual rides:</b> %{customdata[0]:,.0f}<br>"
            "<b>Member rides:</b> %{customdata[1]:,.0f}"
            "<extra></extra>"
        ),
        visible=True
    )
)

# Member rides

chicago_map.add_trace(
    go.Scattermap(
        lat=geo_data["lat_bin"],
        lon=geo_data["lng_bin"],
        mode="markers",
        marker=dict(
            size=geo_data["member"],
            color=geo_data["member"],
            colorscale="BlueRed",
            cmin=color_min,
            cmax=color_max,
            sizemode="area",
            sizeref=sizeref,
            opacity=0.7,
            showscale=True
        ),
        name="Members",
        customdata=geo_data[["member", "casual"]].values,
        hovertemplate=(
            "<b>Member rides:</b> %{customdata[0]:,.0f}<br>"
            "<b>Casual rides:</b> %{customdata[1]:,.0f}"
            "<extra></extra>"
        ),
        visible=False
    )
)

# Dropdown

chicago_map.update_layout(
    updatemenus=[
        dict(
            buttons=[
                dict(
                    label="Casuals",
                    method="update",
                    args=[{"visible": [True, False]}]
                ),
                dict(
                    label="Members",
                    method="update",
                    args=[{"visible": [False, True]}]
                )
            ],
            direction="down",
            showactive=True,
            x=0.02,
            y=0.97
        )
    ],

    map=dict(
        style="open-street-map",
        center=dict(
            lat=41.8781,
            lon=-87.6298
        ),
        zoom=10.5
    ),

    title="Chicago Bike Rides — Members vs Casuals",

    margin={
        "r": 0,
        "t": 40,
        "l": 0,
        "b": 0
    }
)

#Create a second map to isolate the most popular casual ride points of origin.

top5_map = go.Figure()

top_5 = geo_data.nlargest(5, "casual")

top5_map.add_trace(
    go.Scattermap(
        lat=top_5["lat_bin"],
        lon=top_5["lng_bin"],
        mode="markers",
        marker=dict(
            size=top_5["casual"],
            color=top_5["casual"],
            colorscale="BlueRed",
            cmin=color_min,
            cmax=color_max,
            sizemode="area",
            sizeref=sizeref,
            opacity=0.7,
            showscale=True
        ),
        name="Top 5 Casual Locations",
        customdata=top_5[["casual", "member"]].values,
        hovertemplate=(
            "<b>Casual rides:</b> %{customdata[0]:,.0f}<br>"
            "<b>Member rides:</b> %{customdata[1]:,.0f}"
            "<extra></extra>"
        )
    )
)

top5_map.update_layout(
    map=dict(
        style="open-street-map",
        center=dict(
            lat=41.8781,
            lon=-87.6298
        ),
        zoom=10.5
    ),
    title="Top 5 Casual Ride Locations",
    margin=dict(
        r=0,
        t=40,
        l=0,
        b=0
    )
)

## Create interactive dashboard in Streamlit

st.title("Cyclistic Bikeshare Analysis")

## Maps (Two Columns)

map_col1, map_col2 = st.columns (2)

with map_col1:
    st.subheader("Member vs Casual Ride Locations")
    st.plotly_chart(chicago_map)
    
with map_col2:
    st.subheader("Most Popular Casual Ride Locations")
    st.plotly_chart(top5_map)
    
## Graphs (Three Columns)

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Total number of rides")
    st.plotly_chart(fig_total_rides, width = "stretch")
    st.subheader("Rides per Hour by User Type")
    st.plotly_chart(fig_rides_by_hour, width = "stretch")
    
with col2:
    
    st.subheader("Rides by Day of the Week")
    st.plotly_chart(fig_users_by_day, width = "stretch")
    st.subheader("Rides per Month by User Type")
    st.plotly_chart(fig_users_by_month, width = "stretch")
    
with col3:
    
    st.subheader("Average Ride Time")
    st.plotly_chart(fig_ride_time_by_day, width = "stretch")
    st.subheader("Rides per Ride Type by User Type")
    st.plotly_chart(fig_users_by_ridetype, width = "stretch")
