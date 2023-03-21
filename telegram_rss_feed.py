import feedparser
import requests
import ssl
from datetime import datetime, timedelta
import pytz
import sys

FEED_URLS="https://www.berlin.de/en/news/rubric.rss,https://feeds.thelocal.com/rss/de,https://20prozent.substack.com/feed/,https://warnung.bund.de/api31/mowas/rss/110000000000.rss,https://allaboutberlin.com/guides/feed.rss,https://rss.dw.com/rdf/rss-en-ger"

TELEGRAM_BOT_TOKEN = sys.argv[1]
TELEGRAM_CHANNEL_ID = sys.argv[2]
RSS_FEED_URLS = FEED_URLS.split(',')


def send_message(text):
        response = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", {"chat_id": TELEGRAM_CHANNEL_ID,"text": text, "parse_mode": "HTML", "disable_web_page_preview": False})
        if response.status_code == 200:
                print(response.text)
        else:
                print(response.text)


def main():
    german_tz = pytz.timezone("Europe/Berlin")
    now = datetime.now(german_tz)
    hours_ago = now - timedelta(hours=1)  # Get the current date in UTC timezone
    for rss_feed_url in RSS_FEED_URLS:
        if hasattr(ssl, '_create_unverified_context'):
            ssl._create_default_https_context = ssl._create_unverified_context
            feed = feedparser.parse(rss_feed_url)
        last_hours_entries = [entry for entry in feed.entries if hours_ago <= datetime(*entry.published_parsed[:6], tzinfo=pytz.utc).astimezone(german_tz) <= now]
        for entry in last_hours_entries:
            link = entry.link
            message = f"<a href='{link}'>READ HERE</a>"
            send_message(message)

if __name__ == "__main__":
    main()
