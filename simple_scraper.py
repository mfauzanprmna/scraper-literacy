import os
import requests
from bs4 import BeautifulSoup

# ==========================================
# CONFIG
# ==========================================

API_URL         = os.environ.get("API_URL", "https://bijak-ai.web.id/literasense/api/scraping/import")
API_KEY         = os.environ.get("API_KEY", "")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

if not API_KEY:
    raise EnvironmentError("API_KEY environment variable is not set.")

if not YOUTUBE_API_KEY:
    raise EnvironmentError("YOUTUBE_API_KEY environment variable is not set.")

# ==========================================
# DIMENSIONS
# ==========================================

DIMENSIONS = {
    "Conceptual Understanding": [
        "artificial intelligence",
        "machine learning",
        "deep learning",
        "neural network",
        "algoritma",
        "teori",
        "konsep",
        "dasar",
        "kecerdasan buatan",
        "pembelajaran mesin",
        "jaringan saraf"
    ],

    "Application & Skills": [
        "implementasi",
        "python",
        "tensorflow",
        "pytorch",
        "coding",
        "project",
        "build",
        "develop",
        "praktek",
        "hands-on",
        "tutorial",
        "code",
        "program",
        "aplikasi"
    ],

    "Critical Thinking": [
        "analisis",
        "evaluation",
        "strategy",
        "business",
        "roi",
        "impact",
        "comparison",
        "pros cons",
        "decision",
        "optimization",
        "evaluasi",
        "analisa",
        "bisnis",
        "strategi"
    ],

    "Ethical Awareness": [
        "etika",
        "bias",
        "fairness",
        "privacy",
        "safety",
        "responsible",
        "ethics",
        "moral",
        "transparency",
        "accountability",
        "keadilan",
        "privasi",
        "keamanan",
        "tanggung jawab"
    ]
}

# ==========================================
# CLASSIFIER
# ==========================================

class SimpleClassifier:

    def classify(self, text):

        text = text.lower()
        scores = {}

        for dimension, keywords in DIMENSIONS.items():

            matches = 0

            for keyword in keywords:
                if keyword in text:
                    matches += 1

            scores[dimension] = matches / len(keywords)

        if max(scores.values()) == 0:
            return "Other", 0.0

        best_dimension = max(scores, key=scores.get)

        return best_dimension, round(scores[best_dimension], 2)

# ==========================================
# YOUTUBE  (YouTube Data API v3)
# ==========================================

class YouTubeScraper:

    BASE_URL = "https://www.googleapis.com/youtube/v3/search"

    def search(self, keyword):

        try:

            response = requests.get(
                self.BASE_URL,
                params={
                    "part":       "snippet",
                    "q":          keyword,
                    "maxResults": 5,
                    "type":       "video",
                    "key":        YOUTUBE_API_KEY,
                },
                timeout=15
            )

            response.raise_for_status()
            items = response.json().get("items", [])

            data = []

            for item in items:

                video_id = item["id"]["videoId"]
                snippet  = item["snippet"]

                data.append({
                    "title":
                        snippet.get("title", ""),

                    "url":
                        f"https://www.youtube.com/watch?v={video_id}",

                    "description":
                        snippet.get("description", "")[:500],

                    "author":
                        snippet.get("channelTitle", ""),

                    "date":
                        snippet.get("publishedAt", ""),

                    "source":
                        "youtube"
                })

            return data

        except Exception as e:

            print("YouTube Error:", e)
            return []

# ==========================================
# ARXIV
# ==========================================

class JournalScraper:

    def search(self, keyword):

        try:

            url = (
                "http://export.arxiv.org/api/query"
                f"?search_query=all:{keyword}"
                "&start=0"
                "&max_results=5"
            )

            response = requests.get(url, timeout=15)

            soup = BeautifulSoup(
                response.content,
                "xml"
            )

            entries = soup.find_all("entry")

            data = []

            for entry in entries:

                data.append({
                    "title":
                        entry.title.text.strip(),

                    "url":
                        entry.id.text.strip(),

                    "description":
                        entry.summary.text.strip()[:500],

                    "author":
                        ", ".join([
                            a.find("name").text.strip()
                            for a in entry.find_all("author")
                        ]),

                    "date":
                        entry.published.text.strip(),

                    "source":
                        "journal"
                })

            return data

        except Exception as e:

            print("Journal Error:", e)
            return []

# ==========================================
# SEND TO LARAVEL
# ==========================================

def send_to_laravel(contents):

    try:

        response = requests.post(
            API_URL,
            headers={
                "X-API-KEY": API_KEY,
                "Accept":    "application/json"
            },
            json={
                "contents": contents
            },
            timeout=60
        )

        print("Status:", response.status_code)
        print(response.text)

    except Exception as e:

        print("API Error:", e)

# ==========================================
# MAIN SCRAPER
# ==========================================

class SimpleScraper:

    def __init__(self):

        self.classifier = SimpleClassifier()
        self.youtube    = YouTubeScraper()
        self.journal    = JournalScraper()

    def classify_content(self, content):

        text = f"""
        {content['title']}
        {content['description']}
        """

        dimension, confidence = (
            self.classifier.classify(text)
        )

        content["dimension"]  = dimension
        content["confidence"] = confidence

        print(
            f"→ {dimension} ({confidence*100:.0f}%)"
        )

        return content

    def scrape_keyword(self, keyword):

        print(f"\nKeyword: {keyword}")
        print("-" * 50)

        results = []

        yt_results = self.youtube.search(keyword)

        for item in yt_results:
            results.append(
                self.classify_content(item)
            )

        journal_results = self.journal.search(keyword)

        for item in journal_results:
            results.append(
                self.classify_content(item)
            )

        return results

# ==========================================
# RUN
# ==========================================

if __name__ == "__main__":

    scraper = SimpleScraper()

    keywords = [
        "machine learning",
        "deep learning",
        "neural network",
        "artificial intelligence",
        "ai ethics"
    ]

    all_contents = []

    for keyword in keywords:

        contents = scraper.scrape_keyword(
            keyword
        )

        all_contents.extend(contents)

    print(
        f"\nMengirim {len(all_contents)} data ke Laravel..."
    )

    send_to_laravel(all_contents)

    print("\nSelesai")