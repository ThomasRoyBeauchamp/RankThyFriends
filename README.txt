Commands:

!new-game - use this to initialise a game in the current channel
!join-game - use this to join a game (can only be done from game channel, will only take effect at start of next round)
!leave-game - use this to leave a game (will only take effect at start of next round)

!start-game - starts the game
!next - starts the next round (will also skip the current round)
!final-round - indicates that the current round is the final round.

!status will show who still has to submit responses to the questions.

All other interactions are handled by DMs with the bot.

To run, you require an additional file called discordBot.env, with the following format:

DISCORD_TOKEN={discord application API key}
DISCORD_GUILD={ID of discord server/guild}
DEFAULT_CHANNEL_ID={ID of channel to play in}

To install the necessary python packages, run "pip install -r requirements.txt"


On Windows, you may have to activate the Anaconda base environment by running the windows batch script
"C:\Users\{user}\anaconda3\Scripts\activate" before doing the pip install. You can then run the bot with
"python main.py". Note it WILL NOT WORK if you run main.py from within spyder.

When running main.py you can add different options. these are:

-c or -f {file.txt} to choose a list of questions (one per line)
-e {file.env} to specify which .env to load.
