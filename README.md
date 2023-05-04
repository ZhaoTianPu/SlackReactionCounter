# SlackReactionCounter
## Brief description
Slack app for counting the number of reactions in a particular channel and sorting them based on a weighted average or total score. In our group, we use a channel to post relevant papers to our research. Group members then rate each paper for its relevancy, using reactions "1", "2", or "3", with respective weights 1, 2, and 3. Then, to select a paper to present as part of our journal club, we can look at previously posted papers and select from the most relevant ones.
## How to run
To run locally, simply execute `python app.py`, making sure you have all the required packages. Note that the environment variables `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN` and `SLACK_CHANNEL_ID` should be set prior to running the app. This can easily be done by adding a `.env` file next to `app.py`. Next, run `/papers help` in an allowed channel to learn what can be done with this app.
