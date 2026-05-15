#!/usr/bin/env python
# coding: utf-8

# In[1]:


import csv
import pandas as pd
from os import path
import numpy as np
import matplotlib.pyplot as plt
import re
from scipy import interpolate
import numpy.typing as npt
from numpy.random import choice


# In[2]:


pd.set_option('display.max_rows', 15)  # The number of rows above which it'll truncate the dataframe when displaying it. 
pd.set_option('display.min_rows', 10)  # The number of rows it'll be truncated to. 


# ### Reading in the total population for each area

# In[15]:


df_county = pd.read_csv('data/geo_age_1918_round_female_county.csv')
df_county.columns = df_county.columns.str.lstrip('y')
df_county


# In[17]:


df_borough = pd.read_csv('data/geo_age_1918_round_female_borough.csv')
df_borough.columns = df_borough.columns.str.lstrip('y')
df_borough


# In[13]:


df_locations_county = pd.read_csv('data/Geocodes_County_1918.csv')
df_locations_county


# In[12]:


df_locations_borough = pd.read_csv('data/Geocodes_Borough_1918.csv')
df_locations_borough


# In[ ]:


def combine_demography(df_county, df_borough, df_locations_county, df_locations_borough):
    """Combine county and borough demography dataframes with their location data.

    Returns a single DataFrame with columns:
        ID, Name, Latitude, Longitude, 0, 1, ..., 105
    """
    year_cols = [str(i) for i in range(106)]

    # Merge county demography with locations
    county = df_county.merge(df_locations_county[['CountyID', 'Latitude_South', 'Longitude_East']],
                             on='CountyID', how='left')
    county = county.rename(columns={
        'CountyID': 'ID',
        'County': 'Name',
        'Latitude_South': 'Latitude',
        'Longitude_East': 'Longitude',
    })
    county = county[['ID', 'Name', 'Latitude', 'Longitude'] + year_cols]

    # Merge borough demography with locations (strip any whitespace from column names first)
    df_locations_borough.columns = df_locations_borough.columns.str.strip()
    borough = df_borough.merge(df_locations_borough[['BoroughID', 'Latitude_South', 'Longitude_East']],
                               on='BoroughID', how='left')
    borough = borough.rename(columns={
        'BoroughID': 'ID',
        'Borough': 'Name',
        'Latitude_South': 'Latitude',
        'Longitude_East': 'Longitude',
    })
    borough = borough[['ID', 'Name', 'Latitude', 'Longitude'] + year_cols]

    combined = pd.concat([county, borough], ignore_index=True)
    return combined


df_combined = combine_demography(df_county, df_borough, df_locations_county, df_locations_borough)
df_combined


# ### Building hierarchy.csv (ID, Longitude, Latitude, Province)

df_demography = pd.read_csv('clean_data/demography_male.csv', index_col=0)

df_county_male = pd.read_csv('data/geo_age_1918_round_male_county.csv')
df_borough_male = pd.read_csv('data/geo_age_1918_round_male_borough.csv')

province_county = df_county_male[['CountyID', 'Province']].rename(columns={'CountyID': 'ID'})
province_borough = df_borough_male[['BoroughID', 'Province']].rename(columns={'BoroughID': 'ID'})
province_all = pd.concat([province_county, province_borough], ignore_index=True)

hierarchy = df_demography[['ID', 'Longitude', 'Latitude']].merge(province_all, on='ID', how='left')
hierarchy.to_csv('clean_data/hierarchy.csv', index=False)
hierarchy


