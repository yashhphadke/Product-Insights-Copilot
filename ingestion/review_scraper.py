from google_play_scraper import reviews, Sort
from langdetect import detect
import pandas as pd
import emoji
import re
def review_scraper():
    GOOGLE_APP_ID = "com.nextbillion.groww"

    def remove_emojis(text: str) -> str:
        return emoji.replace_emoji(text, replace="")
    def normalize_text(text: str) -> str:
        text = text.lower()

        # Remove URLs
        text = re.sub(r"http\S+|www\S+", "", text)

        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def clean_review_text(text: str) -> str:
        text = remove_emojis(text)
        text = normalize_text(text)

        return text

    all_review_google, token = reviews(
        GOOGLE_APP_ID,
        lang="en",
        country="in",
        sort=Sort.NEWEST,
        count=15000
    )

    cleaned_google = []

    for review in all_review_google:

        raw_review = review["content"]

        # Remove tiny reviews
        if len(raw_review.split()) < 6:
            continue

        # Language filter
        try:
            if detect(raw_review) != "en":
                continue
        except:
            continue
        cleaned_review = clean_review_text(raw_review)
        # Clean review text
        cleaned_google.append(
            {
                "user": review["userName"],
                "rating": review["score"],
                "review": cleaned_review,
                "date": review["at"]
            }
        )

    google_review = pd.DataFrame(cleaned_google)
    google_review.to_csv("./backend/data/review.csv")