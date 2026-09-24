# -*- coding: utf-8 -*-
"""
Created on Wed Aug 12 18:16:05 2026

@author: angus
"""

import pandas as pd
import streamlit as st
import plotly.io as pio
import plotly.express as px
pio.renderers.default = 'browser'
import plotly.graph_objects as go
import requests
from io import BytesIO
from zipfile import ZipFile

st.set_page_config(layout="wide")

#%%

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

@st.cache_data
def read_data():

    all_months = []

    for url in data_urls:
       response = requests.get(url)
       response.raise_for_status()

       with ZipFile(BytesIO(response.content)) as z:

           csv_file = [
               file for file in z.namelist()
               if file.endswith(".csv")
           ][0]

           new_df = pd.read_csv(z.open(csv_file),
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
           all_months.append(new_df)
    return pd.concat(all_months, ignore_index=True)
    
df = read_data()
st.write("✅ Data loaded")
st.write(df.shape)
# %%

# Data cleaning and transformation.

df = df.drop_duplicates(subset = ["ride_id"])

# Add columns showing the month, day of the week, time of day and total time (in seconds) of each ride.

df["started_at"] = pd.to_datetime(df["started_at"])
df["ended_at"] = pd.to_datetime(df["ended_at"])
df["day_of_week"] = df["started_at"].dt.day_name()
df["month"] = df["started_at"].dt.month_name()
df["start_hour"] = df["started_at"].dt.hour
df["ride_length (seconds)"] = ((df["ended_at"] - df["started_at"]).dt.total_seconds()).round().astype(int)

# Filter out classic bike users who have abandoned their bike at an invalid location.
# These rides were automatically ended by Cyclistic after 25 hours and as such are unsuitable for analysis.

df_cleaned = df[(df["rideable_type"] != "classic_bike") | df["end_station_name"].notna()].copy()

# Set day/month order

month_order = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
df_cleaned['month'] = pd.Categorical(df_cleaned['month'], categories=month_order, ordered=True)
df_cleaned['day_of_week'] = pd.Categorical(df_cleaned['day_of_week'], categories=day_order, ordered=True)
# %%

st.write("✅ Data cleaned")
st.write(df_cleaned.shape)

# Analysis Tables

# Create summary table to count total number of member and casual rides.

total_rides = df_cleaned["member_casual"].value_counts()

# Create summary tables to analyse usage rates of casual users and members based on the month and day of the week of each ride.

users_by_hour = df_cleaned.groupby(["start_hour", "member_casual"]).size().unstack()
users_by_day = df_cleaned.groupby(["day_of_week", "member_casual"]).size().unstack()
users_by_month = df_cleaned.groupby(["month", "member_casual"]).size().unstack()

# Create Summary table to analyse users by ride type. To be expressed as a percentage.

users_by_ridetype = df_cleaned.groupby(["rideable_type", "member_casual"]).size().unstack()
users_by_ridetype["casual_pct"] = users_by_ridetype["casual"]/users_by_ridetype["casual"].sum() * 100
users_by_ridetype["member_pct"] = users_by_ridetype["member"]/users_by_ridetype["member"].sum() * 100
# Change ride time from seconds to minutes for readability

avg_seconds = df_cleaned.groupby(["day_of_week", "member_casual"])["ride_length (seconds)"].mean().unstack()
avg_minutes = avg_seconds / 60

#Group rides based on where the ride originated, latitude and longitude rounded to 4 decimal places

df_cleaned["lat_bin"] = df_cleaned["start_lat"].round(4)
df_cleaned["lng_bin"] = df_cleaned["start_lng"].round(4)

geo_data = df_cleaned.groupby(["lat_bin", "lng_bin", "member_casual"]).size().unstack(fill_value = 0).reset_index()
# %%
st.write("✅ Analysis tables created")
st.write("✅ Starting visualisations")

# Visualizations

# Define colour scheme

color_map = {
    "casual": "#f1fb67",
    "member": "#4095a5"
    }

# Total number of rides per user type.

fig_total_rides = px.pie(
    df_cleaned,
    names = "member_casual",
    color = "member_casual",
    color_discrete_map = color_map,
    title = "Total Number of Rides per User Type",
    labels = {
        "casual": "Casual Users",
        "member": "Members"
        },
    )

fig_total_rides.update_traces(hovertemplate="<b>User Type:</b> %{label}<br><b>Total Trips:</b> %{value}<br><b>Share:</b> %{percent}")

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

# %%

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

# %%

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

# %%

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
    st.plotly_chart(fig_total_rides, use_container_width=True)
    st.subheader("Rides per Hour by User Type")
    st.plotly_chart(fig_rides_by_hour, use_container_width=True)
    
with col2:
    
    st.subheader("Rides by Day of the Week")
    st.plotly_chart(fig_users_by_day, use_container_width=True)
    st.subheader("Rides per Month by User Type")
    st.plotly_chart(fig_users_by_month, use_container_width=True)
    
with col3:
    
    st.subheader("Average Ride Time")
    st.plotly_chart(fig_ride_time_by_day, use_container_width=True)
    st.subheader("Rides per Ride Type by User Type")
    st.plotly_chart(fig_users_by_ridetype, use_container_width=True)
