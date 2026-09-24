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

st.title("Divvy Data Test")

url = "https://divvy-tripdata.s3.amazonaws.com/202501-divvy-tripdata.zip"

st.write("Downloading data...")

response = requests.get(url)
response.raise_for_status()

st.write("Download successful!")

with ZipFile(BytesIO(response.content)) as z:

    csv_file = [
        file for file in z.namelist()
        if file.endswith(".csv")
    ][0]

    st.write("CSV found:", csv_file)

    df = pd.read_csv(z.open(csv_file))

st.write("Data loaded successfully!")
st.write("Rows:", len(df))
st.dataframe(df.head())
