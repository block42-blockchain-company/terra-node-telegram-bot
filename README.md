# terra-node-telegram-bot 🌐🤖

A Telegram Bot to monitor the status of Terra Nodes.

Features:
* Monitor **remote nodes**
* Monitor your own **local node**
* Notifications about changes of your node\'s **Jailed**, **Unbonded** or **Delegator Shares** attributes
* Notifications if your **Block Height** gets stuck
* Notifications if **Price Feed** gets unhealthy
* Notifications about new **Governance Proposals**
* Notifications about finished **Governance Proposals**
* Notifications about syncing status changes of your **sentry nodes**
* Voting on **Governance Proposals** from Terra Station Extension
* Voting on **Governance Proposals** using delegation feature
* Notifications on **Slack**

If you have questions please open a [github](https://github.com/block42-blockchain-company/terra-node-telegram-bot/issues) 
issue or contact us in our [Telegram Channel](https://t.me/block42_crypto!)!

## [Requirements](#requirements)
* Telegram
* Docker (if you want to run with docker)
* Python3 (if you want to run without docker)

## [Quickstart](#quickstart)
Install docker and run:

```
docker volume create terra-node-bot-volume
docker run -d --env TELEGRAM_BOT_TOKEN=XXX --env NODE_IP=XXX --env SLACK_WEBHOOK=XXX --env LCD_ENDPOINT=1.2.3.4 --mount source=terra-node-bot-volume,target=/storage block42blockchaincompany/terra-node-bot:latest
```
Set 
- `TELEGRAM_BOT_TOKEN` to your Telegram Bot Token obtained from BotFather.
- `NODE_IP` to any IP you want to monitor (or `localhost`). 
Leave it empty or remove it to only monitor public Node information.
- `SLACK_WEBHOOK` to the webhook of your Slack channel to receive notifications on [Slack](https://slack.com). 
Leave it empty or remove it to not get notified via Slack.
- `LCD_ENDPOINT` to your Node's IP if you have setup the Light Client Daemon on your Node. If not, leave this
variable empty or remove it to use the public `lcd.terra.dev` lcd server.

Optionally set
- `SENTRY_NODES` comma separated list of your sentry nodes' LCD URLs if you want to monitor their sync status.


## [Steps to run everything yourself](#steps-to-run-everything-yourself)
* [Install dependencies](#install-dependencies)
* [Create Telegram Bot token](#create-telegram-bot-token-via-botfather) via [BotFather]((https://t.me/BotFather))
* [Set up Slack Webhook](#set-up-slack-webhook)
* [Set up Light Client Daemon (LCD)](#set-up-lcd)
* [Set environment variables](#set-environment-variables)
* [Start the bot](#start-the-bot)
* [Run and test the bot](#run-and-test-the-bot)
* [Production](#production)
  * [Docker](#docker)
  * [Vote delegation](#vote-delegation)
* [Testing](#testing)
  * [Create new Telegram Client](#create-new-telegram-client)
  * [Sign in to the new Telegram Client](#sign-in-to-the-new-telegram-client)
  * [Install Pytest](#install-pytest)
  * [Run the tests](#run-the-tests)
  * [LocalTerra](#local-terra)

## [Install dependencies](#install-dependencies)
Install all required dependencies via: `pip install -r requirements.txt`

## [Create Telegram Bot token via BotFather](#create-telegram-bot-token-via-botfather)
Start a Telegram chat with [BotFather](https://t.me/BotFather) and click `start`.

Then send `/newbot` in the chat, and follow the given steps to create a new telegram token. Save this token, you will need it in a second.

## [Set up Slack Webhook](#set-up-slack-webhook)
If you want to receive the bot's notifications also in one of your slack channels, you need to set up a Webhook for
your channel.

To do this, follow steps 1, 2, and 3 of the official [Slack guide](https://api.slack.com/messaging/webhooks).
At the end of step 3, you should be able to get your Webhook URL similar to this:
```
https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
```
Save this webhook, you will neet it later.

## [Set up Light Client Daemon (LCD)](#set-up-lcd)
The default configuration of the bot uses the official public LCD endpoint for the queries `lcd.terra.dev`.
This can become an issue when the public endpoint starts rate limiting the requests of the bot.
To prevent this from happening, one can specify his Node's own LCD server as an environment variable.
To set up your own LCD server of your terra node, follow the official docs:
https://docs.terra.money/terracli/lcd.html

## [Set environment variables](#set-environment-variables)
Set the Telegram Bot token you previously created as the environment variable `TELEGRAM_BOT_TOKEN`:
```
export TELEGRAM_BOT_TOKEN=XXX
```
---
Optionally set the Slack Webhook that you previously created as the environment variable `SLACK_WEBHOOK`:
```
export SLACK_WEBHOOK=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
```
---
---
- `SENTRY_NODES` comma separated list of your sentry nodes' LCD URLs if you want to monitor their sync status.
```
export SENTRY_NODES=localhost:1317,192.168.5.4:1317
```
---


Next you can specify the IP of the Terra node that you want to watch in the `NODE_IP` environment variable.

Set it to `localhost` to listen a node on your own machine.

Leave this environment variable empty or don't even set it to only monitor public
node information from the public API endpoint https://lcd.terra.dev/ .

**Make sure that your bot has access to the node API endpoints (specifically `:26657/status`) on this IP.**

*Please note, if you leave `NODE_IP` empty, IP specific monitoring won't take effect (no check for 
increasing block height and catch up status). Because information about block height is private
to each node, we cannot access it without having an IP with an open API endpoint.*
```
export NODE_IP=localhost
```
or
```
export NODE_IP=3.228.22.197
```
---
Another variable you can optionally specify is `LCD_ENDPOINT`:
```
export LCD_ENDPOINT=3.228.22.197
```

Set it to your Node IP. 
If you don't have your own LCD server set up yet, follow the official docs 
https://docs.terra.money/terracli/lcd.html .

Don't set this environment variable to use the public LCD server at `lcd.terra.dev`, but be aware that 
the bot might run into rate limiting issues using this endpoint.

---
Finally, if you want test the Terra Node Monitoring Telegram Bot with data from your local machine, you
need to set the debug environment variable:
```
export DEBUG=True
```
The DEBUG flag set to True will run a local web server as a separate process. 
This way the Telegram Bot can access the local files `validators.json` und `status.json`
in the `test/` folder.

To test whether the bot actually notifies you about changes, the data the bot is querying needs to change. 
You can simulate that by manually editing `test/validators.json` and `test/status.json`.

Furthermore in DEBUG mode separate processes run `test/increase_block_height.py` and `test/update_price_feed.py`.
The former artificially increases the block height so that there are no notifications that the block height got stuck,
and the latter updates the price feed to prevent faulty notifications about the price feeder.
---
If you are using a Jetbrains IDE (e.g. Pycharm), you can set these environment variables for your run 
configuration which is very convenient for development 
(see: https://stackoverflow.com/questions/42708389/how-to-set-environment-variables-in-pycharm).

## [Start the bot](#start-the-bot)
Start the bot via:

```
python3 terra_node_bot.py
```

Make sure that you see a message in the console which indicates that the bot is running.

## [Run and test the bot](#run-and-test-the-bot)
When you created the Telegram Bot token via BotFather, you gave your bot a certain name (e.g. `terranode_bot`). 
Now search for this name in Telegram, open the chat and hit start!

At this point, you can play with the bot, see what it does and check that everything works fine!

The bot persists all data, which means it stores its chat data in the file `storage/session.data`. 
Once you stop and restart the bot, everything should continue as if the bot was never stopped.

If you want to reset your bot's data, simply delete the file `session.data` in the `storage` directory before startup.

## [Production](#production)
In production you do not want to use mock data from the local endpoint but real network data. 
To get real data just set `DEBUG=False` and all other environment variables as 
described in the [Set environment variables](#set-environment-variables) section.

### [Docker](#docker)
To run the bot as a docker container, make sure you have docker installed (see: https://docs.docker.com/get-docker).

Navigate to the root directory of this repository and execute the following commands:

Build the docker image as described in the `Dockerfile`:

```
docker build -t terra-node-bot .
```

To make the bot's data persistent, you need to create a docker volume. If the bot crashes or restarts the volume won't be affected and keeps all the session data:

```
docker volume create terra-node-bot-volume
```

Finally run the docker container:

```
docker run --env TELEGRAM_BOT_TOKEN=XXX --env NODE_IP=XXX --env SLACK_WEBHOOK=XXX --env LCD_ENDPOINT=1.2.3.4 --mount source=terra-node-bot-volume,target=/storage block42blockchaincompany/terra-node-bot:latest
```

Set the `--env TELEGRAM_BOT_TOKEN` flag to your Telegram Bot token.

Set the `--env SLACK_WEBHOOK` flag to your Slack Webhook. To not use slack notifications, 
leave this empty i.e. `--env SLACK_WEBHOOK=` or remove it altogether.

Set the `--env NODE_IP` flag to an IP of a running node or `localhost`.
If you don't know any IP leave this empty i.e. `--env NODE_IP=` or remove it completely.

Set the `--env LCD_ENDPOINT` flag to your node IP if you have set up your own LCD server. Leave it empty
or remove the variable to use the public LCD endpoint at `lcd.terra.dev`.

Finally, the `--mount` flag tells docker to mount our previously created volume in the directory `storage`. 
This is the directory where your bot saves and retrieves the `session.data` file.

*Please note that as docker is intended for production,
there is not the possibility for the `DEBUG` mode when using docker.*

### <a name="vote-delegation">Vote delegation infrastructure</a>
If you want to self host infrastructure for vote delegation - unfortunately you need to set it up 
on your own as this feature is still in beta.

To make it work you need to:
- deploy [website](https://github.com/block42-blockchain-company/terra-telegram-bot-website)
- deploy [backend](https://github.com/block42-blockchain-company/terra-telegram-bot-backend) and connect your own wallet
- setup your own MongoDB database and connect with backend instance
- set correct endpoints in `constants.py`

If you don't do it you can still use all the features provided by the website using the instance 
deployed by block42. Unfortunately, you can't use the backend instance (delegate the voting) as it
 is set up to accept only request from one specific instance of the Telegram bot due to security
 reasons.

## [Testing](#testing)

### [Create new Telegram Client](#create-new-telegram-client)
To test the Terra Node Monitoring Bot, first you need to impersonate your own Telegram Client programmatically.

To do that, you need to obtain your API ID and API hash by creating a 
telegram application that uses your user identity on https://my.telegram.org .
Simply login in with your phone number that is registered on telegram, 
then choose any application (we chose Android) and follow the steps. 

Once you get access to api_id and api_hash, save them in the Environment variables
`TELEGRAM_API_ID` and `TELEGRAM_API_HASH` respectively.
Also save the name of your Telegram Bot without the preceding `@` 
in the `TELEGRAM_BOT_ID` environment variable (e.g. if your bot is named 
`@terra_node_test_bot`, save `terra_node_test_bot` in `TELEGRAM_BOT_ID`).

### [Sign in to the new Telegram Client](#sign-in-to-the-new-telegram-client)
You need to authenticate your new Telegram client with your phone number once to
receive an authentication string.
This cannot be done during the unit test run, that's why there's the separate script
`test/sing_in_telegram.py`. 

Make sure to set the environment variables `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`.
Then run in `test/`
```
python3 sign_in_telegram.py
```
and follow the instructions.
Once finished, the script stores the authentication string in `test/telegram_session.string`
which can be used for the tests.


### [Install Pytest](#install-pytest)
We use `pytest` as the test runner for the tests.
Install `pytest` in the root folder of the repo via:
```
pip install pytest
```

### [Run the tests](#run-the-tests)
You also need to set the `TELEGRAM_BOT_TOKEN` environment variable with your 
Telegram Bot token and set `DEBUG=True` as explained in the [Set environment variables](#set-environment-variables) section.

Keep in mind that the test always deletes the `session.data` file inside `storage/`
in order to have fresh starts for every integration test. If you wish to keep your
persistent data, don't run the tests or comment out 
the line `os.remove("../storage/session.data")` in `test/unit_test.py`.

---
Finally to run the tests open the `test/` folder in your terminal and run
```
pytest -v unit_test.py
```
After all tests finished check that all tests passed.

### <a name="local-terra">LocalTerra</a>
To test the transaction invoking operations, like voting on proposals, you need to set up LocalTerra environment. 
To do it you need docker daemon running. When it's ready just type in these commands:
```
git clone https://www.github.com/terra-project/LocalTerra
cd LocalTerra
docker-compose up
```
You can find more info about LocalTerra [here](https://github.com/terra-project/LocalTerra).