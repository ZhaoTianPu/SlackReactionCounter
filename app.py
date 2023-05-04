from datetime import datetime
import os
import re
import threading
import time
from time import sleep
import textwrap

from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

load_dotenv()
import numpy as np
import requests
from tabulate import tabulate

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

# Verify correct environment variables are set
if "SLACK_BOT_TOKEN" not in os.environ:
    print("Missing environment variable :: SLACK_BOT_TOKEN")
    exit(1)
if "SLACK_APP_TOKEN" not in os.environ:
    print("Missing environment variable :: SLACK_APP_TOKEN")
    exit(1)
if "SLACK_CHANNEL_ID" not in os.environ:
    print("Missing environment variable :: SLACK_CHANNEL_ID")
    exit(1)

# Channel ID
CHANNEL_ID = os.environ["SLACK_BOT_TOKEN"]

# Reactions to parse with associated weights
REACTIONS = {"one": 1, "two": 2, "three": 3}

# Max line width per column for bot output
MAX_WIDTH = 80

# Default number of results to include in summary table
DEFAULT_NUM_RESULTS = 10


# Date parser
def parse_date(date):
    """Parse argument date to days, weeks, months, years"""
    days = 0
    weeks = 0
    months = 0
    years = 0

    last = 0
    for i, dchar in enumerate(date):
        if dchar == "d":
            days = int(date[last:i])
            last = i + 1
        elif dchar == "w":
            weeks = int(date[last:i])
            last = i + 1
        elif dchar == "m":
            months = int(date[last:i])
            last = i + 1
        elif dchar == "y":
            years = int(date[last:i])
            last = i + 1

    return days, weeks, months, years


# Initialize slack app
client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
app = App(token=os.environ["SLACK_BOT_TOKEN"])


@app.command("/papers")
def command_handler(ack, body, respond):
    """Function that responds to /papers command"""
    # Handle arguments
    args = body["text"].split(" ")
    show_total_ranking = False
    date_range = {"d": 0, "w": 0, "m": 2, "y": 0}  # Default, 2 months
    num_results = DEFAULT_NUM_RESULTS

    if "help" in args:
        # Ugly, but does the job
        res = "Paper database ranking counter (/papers)\n\n"
        res += "Options:\n"

        res += "\thelp\n"
        res += "\t\tShow this\n"

        res += "\ttotal\n"
        res += "\t\tShow total number of points ranking instead\n"

        res += "\trange [?d?w?m?y]\n"
        res += "\t\tChange oldest message thread to argument (e.g., *range 3m5d* for 3 months 5 days)\n"

        res += "\tlimit N\n"
        res += "\t\tChange number of results in the ranking\n"

        res += "\tprivate\n"
        res += "\t\tDon't post results in channel"

        return ack({"text": res})
    if "total" in args:
        show_total_ranking = True
    if "range" in args:
        idx = args.index("range")

        if len(args) > idx + 1:
            try:
                (
                    date_range["d"],
                    date_range["w"],
                    date_range["m"],
                    date_range["y"],
                ) = parse_date(args[idx + 1])
            except:
                return ack({"text": "Invalid date range :: " + args[idx + 1]})
    if "limit" in args:
        idx = args.index("limit")

        if len(args) > idx + 1:
            try:
                num_results = int(args[idx + 1])
            except:
                return ack({"text": "Invalid limit :: " + args[idx + 1]})

    # Quickly acknowledge before 3sec timeout
    ack("Generating the list ...")

    # Get channel history
    oldest_time = time.mktime(
        (
            datetime.now()
            + relativedelta(
                days=-date_range["d"],
                weeks=-date_range["w"],
                months=-date_range["m"],
                years=-date_range["y"],
            )
        ).timetuple()
    )
    result = client.conversations_history(
        channel=CHANNEL_ID, limit=1000, oldest=str(oldest_time)
    )

    # Get threads and parse reactions
    threads = []  # List of dict containing information on each paper thread

    def parse_thread(thread):
        """Function for parsing thread --- allows for multi-threading while waiting for title"""
        try:
            # Get text
            text = thread["text"]

            # Get link
            link = re.match(r"<https?://[^\s]+>", text).group()[1:-1].split("|")[0]
            if link is None:
                return  # No link found in thread

            # Get the title of the paper
            r = requests.get(link, timeout=10)
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
                return  # No reactions

            # Eligible thread, add to list
            threads.append(
                {
                    "link": link,
                    "text": text,
                    "rating": rating,
                    "title": html.title.text,
                    "num_votes": sum(rating),
                    "weighted_average": np.round(
                        np.average(list(REACTIONS.values()), weights=rating), 1
                    ),
                    "total_rating": np.dot(list(REACTIONS.values()), rating),
                }
            )
        except AttributeError:
            pass  # No links found

    tasks = []
    for thread in result["messages"]:
        # Run thread
        task = threading.Thread(target=parse_thread, args=(thread,))
        task.start()
        tasks.append(task)

        sleep(0.1)  # Wait a little to not make too many requests

    # Wait for tasks to complete
    for task in tasks:
        task.join()

    # Sort papers by weighted average or total score
    res = ""
    sorted_threads = []
    headers = []

    since_date_str = datetime.utcfromtimestamp(oldest_time).strftime("%Y-%m-%d")
    if show_total_ranking:
        res = "*TOTAL POINTS RANKING SINCE " + since_date_str + "*\n"
        sorted_threads = sorted(
            zip([x["total_rating"] for x in threads], threads),
            key=lambda x: x[0],
            reverse=True,
        )
        headers = ["Rank", "Total Score", "# voters", "Link and title"]
    else:
        res = "*WEIGHTED AVERAGE RANKING SINCE " + since_date_str + "*\n"
        sorted_threads = sorted(
            zip([x["weighted_average"] for x in threads], threads),
            key=lambda x: x[0],
            reverse=True,
        )
        headers = ["Rank", "Avg. Score", "# voters", "Link and title"]

    # Send the results
    table = []
    for rank, thread in enumerate(sorted_threads[:num_results]):
        table.append(
            [
                rank + 1,
                thread[0],
                thread[1]["num_votes"],
                thread[1]["link"]
                + "\n"
                + "\n".join(textwrap.wrap(thread[1]["title"], width=MAX_WIDTH)),
            ]
        )

    res += "```" + tabulate(table, headers=headers) + "```"  # Format results nicely

    respond(
        {
            "response_type": "ephemeral" if "private" in args else "in_channel",
            "text": res,
        }
    )


if __name__ == "__main__":
    # Initialize a Web API client and app
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
