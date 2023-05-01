from bs4 import BeautifulSoup
from datetime import datetime
from dateutil.relativedelta import relativedelta
import numpy as np
import re
import requests
from tabulate import tabulate
import threading
import time
from time import sleep
import textwrap

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

# Slack bot and app tokens
SLACK_BOT_TOKEN = "***REMOVED***"
SLACK_APP_TOKEN = "***REMOVED***"

CHANNEL_ID = "C5G5V0F1U"

REACTIONS = {
    "one": 1,
    "two": 2,
    "three": 3
}

MAX_WIDTH = 80

DEFAULT_NUM_RESULTS = 10

# Initialize a Web API client and app
client = WebClient(token=SLACK_BOT_TOKEN)
app = App(token=SLACK_BOT_TOKEN)

# Date parser
def parse_date(date):
    days = 0
    weeks = 0
    months = 0
    years = 0
    
    last = 0
    for i in range(len(date)):
        if date[i] == "d":
            days = int(date[last:i])
            last = i+1
        elif date[i] == "w":
            weeks = int(date[last:i])
            last = i+1
        elif date[i] == "m":
            months = int(date[last:i])
            last = i+1
        elif date[i] == "y":
            years = int(date[last:i])
            last = i+1

    return days, weeks, months, years

# Function that responds to /papers command
@app.command("/papers")
def command_handler(ack, body, respond):
    # Handle arguments
    args = body["text"].split(" ")
    show_total_ranking = False
    date_range = {"d": 0, "w": 0, "m": 2, "y": 0} # Default, 2 months
    num_results = DEFAULT_NUM_RESULTS

    if "help" in args:
        res = "Paper database ranking counter (/papers)\n\n"
        res += "Options:\n"

        res += "\thelp\n"
        res += "\t\tShow this\n"
        
        res += "\ttotal\n"
        res += "\t\tShow total number of points ranking instead\n"

        res += "\trange [?d?w?m?y]\n"
        res += "\t\tChange oldest message thread to argument (e.g., *range 3m5d* for 3 months 5 days)\n"

        res += "\tlimit N\n"
        res += "\t\tChange number of results in the ranking"
        
        return ack({
            "text": res
            })
    if "total" in args:
        show_total_ranking = True
    if "range" in args:
        idx = args.index("range")

        if len(args) > idx+1:
            try:
                date_range["d"], date_range["w"], date_range["m"], date_range["y"] = parse_date(args[idx+1])
            except:
                return ack({
                    "text": "Invalid date range :: " + args[idx+1]
                })
    if "limit" in args:
        idx = args.index("limit")

        if len(args) > idx+1:
            try:
                num_results = int(args[idx+1])
            except:
                return ack({
                    "text": "Invalid limit :: " + args[idx+1]
                })

    # Quickly acknowledge before 3sec timeout
    ack("Generating the list ...") 

    # Get channel history
    oldest_time = time.mktime((
        datetime.now() 
        + relativedelta(days=-date_range["d"], weeks=-date_range["w"], months=-date_range["m"], years=-date_range["y"]
        )).timetuple())
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
    res = ""
    sorted_threads = []
    headers = []

    since_date_str = datetime.utcfromtimestamp(oldest_time).strftime("%Y-%m-%d")
    if show_total_ranking:
        res = "*TOTAL POINTS RANKING SINCE " + since_date_str + "*\n"
        sorted_threads = sorted(zip([x["total_rating"] for x in threads], threads), key=lambda x: x[0], reverse=True)
        headers = ["Rank", "Total Score", "# voters", "Link and title"]
    else:
        res = "*WEIGHTED AVERAGE RANKING SINCE " + since_date_str + "*\n"
        sorted_threads = sorted(zip([x["weighted_average"] for x in threads], threads), key=lambda x: x[0], reverse=True)
        headers = ["Rank", "Avg. Score", "# voters", "Link and title"]

    # Send the results
    table = []
    for rank, thread in enumerate(sorted_threads[:num_results]):
        table.append(
            [
                rank + 1, 
                thread[0], 
                thread[1]["num_votes"], 
                thread[1]["link"] + "\n" + '\n'.join(textwrap.wrap(thread[1]["title"], width=MAX_WIDTH))
                ])
            
    res += "```" + tabulate(table, headers=headers) + "```"

    respond({
        "response_type": "in_channel",
        "text": res
    })

if __name__ == "__main__":
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
