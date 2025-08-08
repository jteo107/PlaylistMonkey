from dotenv import load_dotenv
import os
from spotipy import Spotify
load_dotenv()
from flask import Flask, render_template, request, session, redirect, url_for
app = Flask(__name__)
from flask import session
from flask import redirect, url_for
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import euclidean_distances





def loadDataField(raw_data,k):
    df = pd.DataFrame(raw_data)
    df = df.dropna()
    df = df.drop_duplicates()
    numeric_df = df.drop(columns='name')
    scalar = StandardScaler()
    df_scaled = scalar.fit_transform(numeric_df)

    kmeans = KMeans(n_clusters=k, random_state=42)
    clusters = kmeans.fit_predict(df_scaled)
    df['cluster'] = clusters
    centers = get_centers(kmeans, df_scaled, df)
    sorted_clusters = sort_clusters(df)

    song_clusters = {}
    for cluster_id in range(k):
        center_name = centers[cluster_id]
        cluster_songs = sorted_clusters[cluster_id]['name']
        song_clusters[f"The {center_name} Cluster"] = cluster_songs.tolist()
    return song_clusters
    
    
def sort_clusters(df):
    clusters = {}
    for i in df['cluster'].unique():
        individual_cluster = df[df['cluster'] == i]
        clusters[i] = individual_cluster
    return clusters

def get_centers(kmeans, df_scaled, df):
    centers = kmeans.cluster_centers_
    distances = euclidean_distances(df_scaled, centers)

    closest_indexes = []
    for i, center in enumerate(centers):
        cluster_indices = np.where(df['cluster'] == i)[0]
        cluster_distances = distances[cluster_indices, i]
        closest_index_in_cluster = cluster_indices[np.argmin(cluster_distances)]
        closest_indexes.append(closest_index_in_cluster)

    closest_points = df.iloc[closest_indexes]
    cluster_names = {}
    for i in range(len(closest_points)):
        name = closest_points.iloc[i]['name']
        cluster_names[i] = name
    return cluster_names
