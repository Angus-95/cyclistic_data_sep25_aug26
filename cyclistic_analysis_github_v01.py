# -*- coding: utf-8 -*-
"""
Created on Wed Aug 12 18:16:05 2026

@author: angus
"""

import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from zipfile import ZipFile


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

        response = requests.get(url, timeout=60)
        response.raise_for_status()

        with ZipFile(BytesIO(response.content)) as z:

            csv_file = [
                file for file in z.namelist()
                if file.endswith(".csv")
            ][0]

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
            
            new_df = new_df.drop_duplicates(subset=["ride_id"])
    
            all_months.append(new_df)

    return pd.concat(all_months, ignore_index=True)


st.title("Cyclistic Test")

st.write("Loading data...")

df = read_data()

st.write("✅ Data loaded")
st.write(df.shape)

# -------------------------
# Cleaning
# -------------------------

st.write("Cleaning data...")

st.write("✅ Duplicates removed")

df["started_at"] = pd.to_datetime(df["started_at"])
df["ended_at"] = pd.to_datetime(df["ended_at"])

st.write("✅ Datetimes converted")

df["day_of_week"] = df["started_at"].dt.day_name()
df["month"] = df["started_at"].dt.month_name()
df["start_hour"] = df["started_at"].dt.hour

st.write("✅ Date columns created")

df["ride_length (seconds)"] = (
    (df["ended_at"] - df["started_at"])
    .dt.total_seconds()
    .round()
    .astype(int)
)

st.write("✅ Ride length calculated")

df_cleaned = df[
    (df["rideable_type"] != "classic_bike")
    | df["end_station_name"].notna()
].copy()

st.write("✅ Invalid rides filtered")

st.write("Final shape:", df_cleaned.shape)
st.dataframe(df_cleaned.head())
