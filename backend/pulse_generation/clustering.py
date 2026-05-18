import numpy as np
import pandas as pd
import umap
import os
import hdbscan


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(
    BASE_DIR,
    "..",
    "data"
)

REVIEWS_PATH = os.path.join(DATA_DIR, "review.csv")

EMBEDDINGS_PATH = os.path.join(DATA_DIR, "embeddings.npy")

def get_clusters(week,min_rating,max_rating):
    df = pd.read_csv(
        REVIEWS_PATH
    )

    df["date"] = pd.to_datetime(
        df["date"]
    )

    cutoff_date = (
        pd.Timestamp.today()
        - pd.Timedelta(weeks=week)
    )

    filtered_df = df[
        (
            df["date"] >= cutoff_date
        )
        &
        (
            df["rating"] >= min_rating
        )
        &
        (
            df["rating"] <= max_rating
        )
    ].copy()

    print("\nFiltered Reviews Shape:")
    print(filtered_df.shape)

    embeddings = np.load(
        EMBEDDINGS_PATH
    )

    print("\nOriginal Embeddings Shape:")
    print(embeddings.shape)

    filtered_embeddings = embeddings[
        filtered_df.index
    ]

    print("\nFiltered Embeddings Shape:")
    print(filtered_embeddings.shape)

    reducer = umap.UMAP(
        n_neighbors=15,
        n_components=5,
        metric="cosine",
        random_state=42
    )

    reduced_embeddings = (
        reducer.fit_transform(
            filtered_embeddings
        )
    )

    print("\nReduced Embeddings Shape:")
    print(reduced_embeddings.shape)

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=5,
        metric="euclidean",
        cluster_selection_method="eom"
    )

    cluster_labels = (
        clusterer.fit_predict(
            reduced_embeddings
        )
    )


    filtered_df["cluster"] = (
        cluster_labels
    )

    filtered_df["cluster_confidence"] = (
        clusterer.probabilities_
    )
    return filtered_df