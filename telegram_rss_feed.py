import feedparser
import requests
import ssl
import pytz
import sys
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import logging
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
cred = credentials.Certificate('german-news-script-firebase-adminsdk.json')
firebase_admin.initialize_app(cred)

logging.basicConfig(level=logging.INFO)

FEED_URLS="https://www.berlin.de/en/news/rubric.rss," \
          "https://feeds.thelocal.com/rss/de," \
          "https://20prozent.substack.com/feed/," \
          "https://warnung.bund.de/api31/mowas/rss/110000000000.rss," \
          "https://allaboutberlin.com/guides/feed.rss," \
          "https://rss.dw.com/atom/rss-en-ger," \
          "https://www.deutschland.de/en/feed-news/rss.xml"

TELEGRAM_BOT_TOKEN = sys.argv[1]
TELEGRAM_CHANNEL_ID = "@sheroziy_test"
RSS_FEED_URLS = FEED_URLS.split(',')

DELAY_BETWEEN_REQUESTS = 2  # in seconds


def extract_image_url(message, url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Error fetching the URL: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    image = soup.find("meta", attrs={"property": "og:image"}) or \
            soup.find("meta", attrs={"name": "twitter:image"}) or \
            soup.find("meta", attrs={"name": "twitter:image:src"})
    image_url = image["content"] if image else "No image URL found"

    try:
        send_photo_message(image_url, message)
        logging.info(f"Image URL: {image_url}")
    except requests.RequestException as e:
        logging.error(f"Error fetching the URL: {e}")
    return None


def send_photo_message(link, text):
    photo_message_response = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", {"chat_id": TELEGRAM_CHANNEL_ID,
                                                                                                          "parse_mode": "HTML",
                                                                                                          "photo": link,
                                                                                                          "caption": text})
    if photo_message_response.status_code == 200:
        logging.info("News Sent Successfully")
    else:
        logging.error(photo_message_response.text)


def get_feed_entries(rss_feed_url):
    if hasattr(ssl, '_create_unverified_context'):
        ssl._create_default_https_context = ssl._create_unverified_context
    return feedparser.parse(rss_feed_url).entries


def filter_entries(last_hour_entries):
    deduplicated_entries = []
    seen_links = set()
    seen_titles = set()
    for entry in last_hour_entries:
        if entry.link not in seen_links and entry.title not in seen_titles:
            deduplicated_entries.append(entry)
            seen_links.add(entry.link)
            seen_titles.add(entry.title)
    return deduplicated_entries


def main():
    german_tz = pytz.timezone("Europe/Berlin")
    now = datetime.now(german_tz)
    one_hour_ago = now - timedelta(hours=12)

    last_hour_entries = []

    for rss_feed_url in RSS_FEED_URLS:
        last_hour_entries.extend(get_feed_entries(rss_feed_url))

    last_hour_entries = [entry for entry in last_hour_entries if
                         one_hour_ago <= datetime(*entry.published_parsed[:6], tzinfo=pytz.utc).astimezone(german_tz) <= now]

    last_hour_entries = filter_entries(last_hour_entries)

    db = firestore.client()
    collection_ref = db.collection('news_articles')  # Using a consistent collection name

    for entry in last_hour_entries:
        link = entry.link
        title = entry.title

        # Check if the entry already exists in Firestore
        docs = collection_ref.where('link', '==', link).stream()
        if any(doc for doc in docs):
            logging.info(f"Duplicate detected for the link: {link}. Skipping...")
            continue

        # Otherwise, store the entry in Firestore
        collection_ref.add({
            'title': title,
            'link': link
        })

        description = entry.description
        source = link.split('/')[2]
        message = f"<strong>{title}</strong>\n" \
                  f"\n{description}" \
                  f"\n\nSource: {source}" \
                  f"\n\n<a href='{link}'>READ HERE</a>"
        extract_image_url(message, link)
        time.sleep(DELAY_BETWEEN_REQUESTS)

if __name__ == "__main__":
    main()
