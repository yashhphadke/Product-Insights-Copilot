from sentence_transformers import SentenceTransformer
import pandas as pd
import numpy as np
from fee_scrape import fee_scraper
from review_scraper import review_scraper
import time

def main():
    start = time.time()
    print(start)
    review_scraper()
    review_scraper_time = time.time()
    print("time taken for review scraping: {}s".format(review_scraper_time-start))
    fee_scraper()
    fee_scraper_time =  time.time()
    print("time taken for fee scraping: {}s".format(fee_scraper_time-fee_scraper_time))

    MODEL_NAME = "all-MiniLM-L6-v2"

    model = SentenceTransformer(MODEL_NAME)


    def generate_embeddings(texts,batch_size=128):
        embeddings = model.encode(texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        return embeddings


    def generate_review_embeddings(df
    ):

        review_texts = (df["review"].fillna("").astype(str).tolist())

        embeddings_final = (
            generate_embeddings(
                review_texts,
                batch_size=128
            )
        )

        return (df,embeddings_final)
    df = pd.read_csv("./backend/data/review.csv")
    filtered_df, embeddings = (generate_review_embeddings(df))

    print("\nFiltered Reviews:")
    print(filtered_df.shape)

    print("\nEmbeddings Shape:")
    print(embeddings.shape)
    np.save("./backend/data/embeddings.npy",embeddings)
    embeddings_time =  time.time()
    print("time taken for embedding generation: {}s".format(embeddings_time-fee_scraper_time))
    print("total time taken{}s".format(embeddings_time-start))


if __name__ == "__main__":
    main()