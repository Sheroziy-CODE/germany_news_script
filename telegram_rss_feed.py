import feedparser
import requests
import ssl
import pytz
import sys
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

FEED_URLS="https://www.berlin.de/en/news/rubric.rss," \
          "https://feeds.thelocal.com/rss/de," \
          "https://20prozent.substack.com/feed/," \
          "https://warnung.bund.de/api31/mowas/rss/110000000000.rss," \
          "https://allaboutberlin.com/guides/feed.rss," \
          "https://rss.dw.com/atom/rss-en-ger"

TELEGRAM_BOT_TOKEN = sys.argv[1]
TELEGRAM_CHANNEL_ID = sys.argv[2]
RSS_FEED_URLS = FEED_URLS.split(',')


def extract_image_url(message, url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    image = soup.find("meta", attrs={"property": "og:image"}) or \
            soup.find("meta", attrs={"name": "twitter:image"}) or \
            soup.find("meta", attrs={"name": "twitter:image:src"})
    image_url = image["content"] if image else "No image URL found"

    try:
        send_photo_message(image_url, message)
        print(f"Image URL: {image_url}")
    except requests.RequestException as e:\
        print(f"Error fetching the URL: {e}")
    return None


def send_photo_message(link, text):
    photo_message_response = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", {"chat_id": TELEGRAM_CHANNEL_ID,
                                                                                                          "parse_mode": "HTML",
                                                                                                          "photo": link,
                                                                                                          "caption": text})
    if photo_message_response.status_code == 200:
        print("News Sent Success")
    else:
        print(photo_message_response.text)


def main():
    german_tz = pytz.timezone("Europe/Berlin")
    now = datetime.now(german_tz)
    three_hours_ago = now - timedelta(hours=24)
    for rss_feed_url in RSS_FEED_URLS:
        if hasattr(ssl, '_create_unverified_context'):
            ssl._create_default_https_context = ssl._create_unverified_context
            feed = feedparser.parse(rss_feed_url)
        last_3_hours_entries = [
            entry for entry in feed.entries if
            three_hours_ago <= datetime(*entry.updated_parsed[:6],tzinfo=pytz.utc).astimezone(german_tz) <= now
        ]
        for entry in last_3_hours_entries:
            link = entry.link
            title = entry.title
            description = entry.description
            source = link.split('/')[2]
            message = f"<strong>{title}</strong>\n" \
                      f"\n{description}" \
                      f"\n\nSource: {source}" \
                      f"\n\n<a href='{link}'>READ HERE</a>"
            extract_image_url(message, link)

if __name__ == "__main__":
    main()
