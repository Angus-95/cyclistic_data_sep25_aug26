# -*- coding: utf-8 -*-
"""
Created on Wed Aug 12 18:16:05 2026

@author: angus
"""

import streamlit as st
import pandas as pd
import plotly.express as px

st.title("Divvy Dashboard Test")

st.write("Streamlit is working!")
st.write("Pandas version:", pd.__version__)

fig = px.bar(
    x=["Classic", "Electric"],
    y=[20, 80],
    labels={"x": "Bike Type", "y": "Percentage"}
)

st.plotly_chart(fig)
