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

st.title("Divvy 12 Month Test")

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

st.write("🚀 App started")

all_months = []

for i, url in enumerate(data_urls):

    st.write(f"Downloading month {i + 1} of {len(data_urls)}...")

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

        all_months.append(new_df)

    st.write(f"✅ Month {i + 1} loaded — {len(new_df):,} rows")

st.write("Combining data...")

df = pd.concat(all_months, ignore_index=True)

st.write("🎉 Everything loaded!")
st.write(f"Total rows: {len(df):,}")
st.dataframe(df.head())
