# SlackReactionCounter
## Brief description
Slack app for counting the number of reactions in a particular channel and sorting them based on a weighted average or total score. In our group, we use a channel to post relevant papers to our research. Group members then rate each paper for its relevancy, using reactions :one:, :two:, or :three: (corresponding to emojis `:one:`, `:two:` and `:three:`), with respective weights 1, 2, and 3. Then, to select a paper to present as part of our journal club, we look at previously posted papers and select from the most relevant ones.
## Requiremenets
We haven't yet tested versions above/below the following specifications
```
beautifulsoup4==4.12.2
bs4==0.0.1
certifi==2022.12.7
charset-normalizer==3.1.0
idna==3.4
numpy==1.24.3
python==3.10
python-dateutil==2.8.2
python-dotenv==1.0.0
requests==2.30.0
six==1.16.0
slack-bolt==1.18.0
slack-sdk==3.21.3
soupsieve==2.4.1
tabulate==0.9.0
urllib3==2.0.2
```
## How to install
Run
```
git clone https://github.com/ZhaoTianPu/SlackReactionCounter
```
in a desired directory to create a folder `SlackReactionCounter` with codes. Alternatively, download through GitHub and unzip.
## Configuring a Slack bot in your Slack workspace
You need to create and configure a Slack bot in your Slack workspace first, before running the code.
1. Go to https://api.slack.com, after logging in, click `Your Apps` on top right corner.
2. Create the bot: Click `Create New App` and then click `From scratch`, then provide your app name and specify the workspace where the app will be installed.
3. After we have created the bot, we will be redirected to the bot’s configuration page. Under the `Features` section in the left panel, go to the `OAuth & Permissions` tab. Navigate down to `Bot Token Scopes` under `Scopes` and add the following scopes to grant necessary permissions for the bot:
    1. `app_mentions:read`
    2. `channels:history`
    3. `channels:read`
    4. `channels:write`
    5. `chat:write`
    6. `commands`
    7. `reactions:read`
4. Navigate down to `User Token Scopes` and add the following scopes:
    1. `channels:history`
    2. `channels:read`
    3. `chat:write`
    4. `reactions:read`
5. Enable slash commands: Under the `Features` section in the left panel, go to the `Slash Commands` tab. Create your own commands here. We use `/papers` in our group as the command.
6. Install the bot. Under the `Settings` section in the left panel, go to the `Install App` tab and install/reinstall to the workspace. Copy `User OAuth Token` and `Bot User OAuth Token`.
7. You will also need to get the ID of the Slack channel, from which threads will be ranked based on the reaction emojis. To obtain this, open your Slack workspace and click on the target channel, and the url reads: https://app.slack.com/client/`&lt;workspace id&gt;`/`&lt;channel id&gt;`. Copy the `&lt;channel id&gt;` here.
## How to run locally
To run locally, simply execute `python app.py`, making sure you have all the required packages. Note that the environment variables `SLACK_BOT_TOKEN` (set the value to `Bot User OAuth Token`), `SLACK_APP_TOKEN` (set the value to `User OAuth Token`) and `SLACK_CHANNEL_ID` (set the value to `&lt;channel id&gt;`) should be set prior to running the app. This can easily be done by adding a `.env` file next to `app.py`. Next, run `/papers help` in an allowed channel to learn what can be done with this app.
## How to host on AWS
To host on AWS, it is much more involved, but thankfully can be achieved with the free tier (max 1M requests per month). First, due to the 3 sec timeout set by Slack, the dispatcher `dispatcher.py` must be in its own AWS Lambda function that has publishing access to a SNS. Additionally, an AWS lambda API Gateway trigger must be added and set as the Slack app request URL.

Next, the actual app should reside in another AWS Lambda function that triggers on an SNS event. Since AWS Lambda doesn't have all Python packages, you need to package the virtual environment Python packages (specifically `[virtualenv]/lib/python3.**/site-packages`, here packaged as `packages-python-3-10.zip`) with the python files `app.py`, `utils.py`, and `aws_app.py` into a zip file (here `app.zip`, generated with `package.sh`) and upload it to AWS. The environment variables (`SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN` and `SLACK_CHANNEL_ID`) can be set directly in the AWS dashboard. Note that the python version used in the virtual environment should match the one on AWS, as well as the operating system for packages such as `numpy`. Finally, because the app execution takes longer than 3 seconds, the timeout of the AWS Lambda function should be increased to a couple of minutes.  