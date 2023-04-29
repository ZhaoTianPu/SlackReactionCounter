""" 
Ref: https://api.slack.com/messaging/retrieving
"""

# for getting current time and specify the time range for messages
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

# need to install these packages before running
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

import logging

# for getting the paper titles
import re
import requests
from bs4 import BeautifulSoup

# Import WebClient from Python SDK (github.com/slackapi/python-slack-sdk)
# WebClient instantiates a client that can call API methods
# When using Bolt, you can use either `app.client` or the `client` passed to listeners.


logger = logging.getLogger(__name__)

# slack bot and app tokens
SLACK_BOT_TOKEN = "***REMOVED***"
SLACK_APP_TOKEN = "***REMOVED***"

# Initialize a Web API client and app
client = WebClient(token=SLACK_BOT_TOKEN)
app = App(token=SLACK_BOT_TOKEN)


# This is the function that will be called when the bot is mentioned
@app.event("app_mention")
def mention_handler(body, say):
    # first define the range of time we want to get the messages
    shift_time = relativedelta(months=-2)
    # calculate the unix time for the earliest message we want to get
    unix_time = time.mktime((datetime.now() + shift_time).timetuple())

    # get the channel id for the channel we want to get the messages from
    channel_id = "C5G5V0F1U"  # paper channel id

    # get the messages from the channel
    result = client.conversations_history(
        channel=channel_id, limit=1000, oldest=str(unix_time)
    )

    # get the messages and the reactions
    conversation_history = result["messages"]
    texts = []
    ratings = []
    titles = []
    # for each message, get the text and count the number of "one", "two", "three" reactions
    for thread in conversation_history:
        text = thread["text"]
        # get the title of the paper
        # first try to get the link, if there is no link, then skip this message
        try:
            link = re.search(r"<(https?.*?)>", text).group(1)
            # get rid of any \ in the link
            link = link.replace("\\", "")
            # # get the title of the paper
            # page = requests.get(link)
            # soup = BeautifulSoup(page.content, "html.parser")
            # titles.append(soup.title.get_text())
            texts.append(text)
            rating = [0, 0, 0]
            # count the number of "one", "two", "three" reactions
            # if there is no reaction, then the rating will be [0, 0, 0]
            try:
                reactions = thread["reactions"]
                for reaction in reactions:
                    if reaction["name"] == "one":
                        rating[0] = reaction["count"]
                    elif reaction["name"] == "two":
                        rating[1] = reaction["count"]
                    if reaction["name"] == "three":
                        rating[2] = reaction["count"]
            except KeyError:
                pass
            ratings.append(rating)
        except AttributeError:
            pass
    # an example print message
    printstring = f""
    # calculate the weighted average and total scores for each paper, rank them and print the results out
    total_scores = []
    weighted_averages = []
    num_voters = []
    for rating in ratings:
        rating_sum = sum(rating)
        if rating_sum == 0:
            weighted_average = 0
        else:
            weighted_average = (rating[0] + 2 * rating[1] + 3 * rating[2]) / sum(rating)
        weighted_averages.append(weighted_average)
        total_score = rating[0] + 2 * rating[1] + 3 * rating[2]
        num_voters.append(rating_sum)
        total_scores.append(total_score)
    # sort the papers by weighted average and total score
    sorted_by_weighted_average = sorted(
        zip(weighted_averages, num_voters, texts), reverse=True
    )
    sorted_by_total_score = sorted(zip(total_scores, num_voters, texts), reverse=True)
    # print the results
    printstring += f"Weighted average ranking for papers within last 2 months:\n"
    printstring += f"rank | avg. score | # voter | link \n"
    for ranking, paper in enumerate(sorted_by_weighted_average[:10]):
        printstring += f"{ranking + 1} | {paper[0]} | {paper[1]} | {paper[2]} \n"
    printstring += f"\nTotal score ranking for papers within last 2 months:\n"
    printstring += f"rank | ttl. score | # voter | link \n"
    for ranking, paper in enumerate(sorted_by_total_score[:10]):
        printstring += f"{ranking + 1} | {paper[0]} | {paper[1]} | {paper[2]} \n"
    say(printstring)


# I know nothing about this part, just copy and paste
if __name__ == "__main__":
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)

    handler.start()
