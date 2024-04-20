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