import gspread
import pytz
import tweepy
import yaml

from calendar import TUESDAY
from datetime import date, datetime, timedelta
from gspread_formatting import set_column_width, set_frozen

with open('config.yaml') as f:
    config = yaml.safe_load(f)

client = tweepy.Client(config['bearer-token'])
gc = gspread.service_account(config['service-acount-path']) 

def get_contest_tweet():
    today = date.today()
    offset = today.weekday() - TUESDAY
    tues = today - timedelta(days=offset)

    start = datetime.combine(tues, datetime.min.time()).astimezone(pytz.UTC)
    end = datetime.combine(tues, datetime.max.time()).astimezone(pytz.UTC)

    tweet = client.search_recent_tweets('from:stellaphone #crypticcluecontest',
                                         start_time=start,
                                         end_time=end).data[-1]

    return tweet


def get_replies(tweet_id):
    results = client.search_recent_tweets(
                     f'conversation_id:{tweet_id}',
                     tweet_fields='public_metrics,referenced_tweets',
                     expansions='author_id',
                     user_fields='username',
                     max_results=100)

    users = {}
    replies = []

    for u in results.includes['users']:
        users[u.id] = u.username

    for t in results.data:
        if not any(tweet.id == tweet_id for tweet in t.referenced_tweets):
            continue
        reply = {}
        reply['username'] = f'@{users[t.author_id]}'
        reply['text'] = t.text[len('@stellaphone '):]
        reply['likes'] = t.public_metrics['like_count']
        reply['url'] = f'https://twitter.com/{users[t.author_id]}/status/{t.id}'
        replies.append(reply)

    return replies

def post_to_google_doc(replies, answer):
    sh = gc.open('Weekly Cryptic Contest')
    ws = sh.add_worksheet(title=answer, index=0, rows="100", cols="4")
    
    ws.update('A1:D1', [['username','tweet','likes','url']])

    row_num = 1
    
    updates = []
    for r in replies:
        row_num += 1
        updates.append([r['username'], r['text'],r['likes'], r['url']])

    ws.update(f'A2:D{row_num}', updates)

    ws.format(f'B1:B{row_num}', {'wrapStrategy':'WRAP'})

    set_column_width(ws, 'A', 150)
    set_column_width(ws, 'B', 350)
    set_column_width(ws, 'C',  50)
    set_column_width(ws, 'D', 350)

    set_frozen(ws, rows=1)

def main():
    tweet = get_contest_tweet()

    tweet_id = tweet.id
    tweet_text = tweet.text.split()

    possible_answers = [w for w in tweet_text if len(w) >= 4 and w == w.upper()]

    if possible_answers:
        answer = possible_answers[-1]
    else:
        answer = f'New contest {datetime.today().isoformat()}'

    replies = get_replies(tweet_id)
    replies.sort(key=lambda t: t['likes'], reverse=True)

    post_to_google_doc(replies, answer)

main()
