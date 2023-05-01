# for getting current time and specify the time range for messages
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

# need to install these packages before running
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

import numpy as np
import threading
from time import sleep
import textwrap

# for getting the paper titles
import re
import requests
from bs4 import BeautifulSoup
from tabulate import tabulate

# slack bot and app tokens
SLACK_BOT_TOKEN = "***REMOVED***"
SLACK_APP_TOKEN = "***REMOVED***"

CHANNEL_ID = "C5G5V0F1U"

REACTIONS = {
    "one": 1,
    "two": 2,
    "three": 3
}

MAX_WIDTH = 80

NUM_RESULTS = 10

# Initialize a Web API client and app
client = WebClient(token=SLACK_BOT_TOKEN)
app = App(token=SLACK_BOT_TOKEN)

# Function that responds to /papers command
@app.command("/papers")
def command_handler(ack, body, respond):
    # Quickly acknowledge before 3sec timeout
    ack("Generating the list ...") 

    # Get channel history
    oldest_time = time.mktime((datetime.now() + relativedelta(months=-2)).timetuple())
    result = client.conversations_history(
        channel=CHANNEL_ID, limit=1000, oldest=str(oldest_time)
    )

    # Get threads and parse reactions
    threads = []

    # Function for parsing thread --- allows for multi-threading while waiting for title
    def parse_thread(thread):
        try:
            # Get text
            text = thread["text"]

            # Get link
            link = re.match(r"<?https?://[^\s]+>", text).group()[1:-1].split("|")[0]
            if link is None:
                return # No link found in thread

            # Get the title of the paper
            r = requests.get(link)
            html = BeautifulSoup(r.text, "html.parser")

            # Compute rating
            rating = [0] * len(REACTIONS)
            if "reactions" in thread:
                thread_reactions = thread["reactions"]
                for thread_reaction in thread_reactions:
                    for i, (reaction, weight) in enumerate(REACTIONS.items()): 
                        if thread_reaction["name"] == reaction:
                            rating[i] = thread_reaction["count"]

            if sum(rating) == 0:
                return # No reactions

            # Eligible thread, add to list
            threads.append({
                "link": link,
                "text": text,
                "rating": rating,
                "title": html.title.text,
                "num_votes": sum(rating),
                "weighted_average": np.round(np.average(list(REACTIONS.values()), weights=rating), 1),
                "total_rating": np.dot(list(REACTIONS.values()), rating)
            })
        except AttributeError:
            pass # No links found

    tasks = []
    for thread in result["messages"]:
        # Run thread
        task = threading.Thread(target=parse_thread, args=(thread,))
        task.start()
        tasks.append(task)

        sleep(0.1) # Wait a little to not make too many requests
    
    # Wait for tasks to complete
    for task in tasks:
        task.join()

    # Sort papers by weighted average and total score
    sorted_by_weighted_average = sorted(zip([x["weighted_average"] for x in threads], threads), key=lambda x: x[0], reverse=True)
    sorted_by_total_rating = sorted(zip([x["total_rating"] for x in threads], threads), key=lambda x: x[0], reverse=True)

    # Send the results
    table = []
    for rank, thread in enumerate(sorted_by_weighted_average[:NUM_RESULTS]):
        table.append(
            [
                rank + 1, 
                thread[0], 
                thread[1]["num_votes"], 
                thread[1]["link"] + "\n" + '\n'.join(textwrap.wrap(thread[1]["title"], width=MAX_WIDTH))
                ])
            
    res = "*WEIGHTED AVERAGE RANKING FOR THE LAST 2 MONTHS*\n"
    res += "```" + tabulate(table, headers=("Rank", "Avg. Score", "# voters", "Link and title")) + "```"

    respond({
        #"response_type": "in_channel",
        "text": res
    })

if __name__ == "__main__":
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
