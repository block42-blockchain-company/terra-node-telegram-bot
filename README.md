# terra-node-telegram-bot 🌐🤖

A telegram bot to monitor the status of Terra Nodes.

If you have questions feel free to open a github issue or contact us in our Telegram Channel https://t.me/block42_crypto!

## Requirements
* Telegram
* Docker (if you want to run with docker)
* Python3 (if you want to run without docker)

## Quickstart
Install docker and run:

```
docker volume create terra-node-bot-volume
docker run -d --env TELEGRAM_BOT_TOKEN=XXX --env NODE_IP=XXX --mount source=terra-node-bot-volume,target=/storage block42blockchaincompany/terra-node-bot:latest
```
Set 
- `TELEGRAM_BOT_TOKEN` to your Telegram Bot Token obtained from BotFather.
- `NODE_IP` to any IP you want to monitor (or `localhost`). 
Leave it empty or remove it to only monitor public Node information.

## Steps to run everything yourself
* Install dependencies
* Create Telegram bot token via [BotFather](https://t.me/BotFather)
* Set environment variables
* Start the bot
* Run & test the bot
* Production
* Testing

## Install dependencies
Install all required dependencies via: `pip install -r requirements.txt`

## Create Telegram bot token via BotFather
Start a Telegram chat with [BotFather](https://t.me/BotFather) and click `start`.

Then send `/newbot` in the chat, and follow the given steps to create a new telegram token. Save this token, you will need it in a second.

## Set environment variables
Set the telegram bot token you just created as an environment variable: `TELEGRAM_BOT_TOKEN`

```
export TELEGRAM_BOT_TOKEN=XXX
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
Finally, if you want test the Terra Node Monitoring Telegram Bot with data from your local machine, you
need to set the debug environment variable:
```
export DEBUG=True
```
The DEBUG flag set to True will run a local web server as a separate process. 
This way the telegram bot can access the local files `validators.json` und `status.json`
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

## Start the bot
Start the bot via:

```
python3 terra_node_bot.py
```

Make sure that you see a message in the console which indicates that the bot is running.

## Run & test the bot
When you created the telegram bot token via BotFather, you gave your bot a certain name (e.g. `terranode_bot`). 
Now search for this name in Telegram, open the chat and hit start!

At this point, you can play with the bot, see what it does and check that everything works fine!

The bot persists all data, which means it stores its chat data in the file `storage/session.data`. 
Once you stop and restart the bot, everything should continue as if the bot was never stopped.

If you want to reset your bot's data, simply delete the file `session.data` in the `storage` directory before startup.

## Production
In production you do not want to use mock data from the local endpoint but real network data. 
To get real data just set `DEBUG=False` and all other environment variables as 
described in the 'Set environment variables' section.

### Docker
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
docker run --env TELEGRAM_BOT_TOKEN=XXX --env NODE_IP=XXX --mount source=terra-node-bot-volume,target=/storage block42blockchaincompany/terra-node-bot:latest
```

Set the `--env TELEGRAM_BOT_TOKEN` flag to your telegram bot token. 

Set the `--env NODE_IP` flag to an IP of a running node, or remove 
`--env NODE_IP=XXX` to listen on localhost.
If you don't know any IP leave this empty i.e. `--env NODE_IP=` or remove it completely.

Finally, the `--mount` flag tells docker to mount our previously created volume in the directory `storage`. 
This is the directory where your bot saves and retrieves the `session.data` file.

*Please note that as docker is intended for production,
there is not the possibility for the `DEBUG` mode when using docker.*


## Testing

### Create new Telegram Client
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

### Sign in to the new Telegram Client
You need to authenticate your new Telegram client with your phone number once to
receive an authentication string.
This cannot be done during the unit test run, that's why there's the separate script
`test/sing_in_telegram.py`. 

Make sure to set the environment variables `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`.
Then run in `test/`
```
python3 sing_in_telegram.py
```
and follow the instructions.
Once finished, the script stores the authentication string in `test/telegram_session.string`
which can be used for the tests.


### Install Pytest
We use `pytest` as the test runner for the tests.
Install `pytest` in the root folder of the repo via:
```
pip install pytest
```

### Run the tests
You also need to set the `TELEGRAM_BOT_TOKEN` environment variable with your 
telegram bot token and set `DEBUG=True` as explained in previous sections.

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
