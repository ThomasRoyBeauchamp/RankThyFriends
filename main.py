import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from RankingGame import RankingGame

import logging
import argparse


if __name__ == '__main__':

    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("--categories", "-c", "-f",
                                 required=False,
                                 default=None,
                                 help="Line-separated file of all the categories to be played.")
    argument_parser.add_argument("--environment", "-e", required=False,default=None, help="Name of .env file to load")

    args = argument_parser.parse_args()

    if args.categories is None:
        file_to_load = "categories.txt"
    else:
        file_to_load = args.categories




    categories = []
    with open(file_to_load, 'r') as F:
        for line in F:
            if line != '\n':
                categories.append(line.replace('\n',''))

    if args.environment is None:
        load_dotenv('discordBot.env')
    else:
        load_dotenv(args.environment)

    TOKEN = os.getenv('DISCORD_TOKEN')
    GUILD = int(os.getenv('DISCORD_GUILD'))
    CHANNEL_ID = int(os.getenv('DEFAULT_CHANNEL_ID'))




    intents = discord.Intents.default()
    intents.message_content = True

    game_instance: RankingGame = RankingGame(channel_id=CHANNEL_ID, categories=categories)

    game_log = logging.getLogger('RankYourFriends_Log')
    game_log.setLevel('INFO')
    fmt = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
    syslog = logging.StreamHandler()
    syslog.setFormatter(fmt)
    game_log.addHandler(syslog)


    bot = commands.Bot(command_prefix='!', intents=intents)




    @bot.event
    async def on_ready():
        print(f'{bot.user.name} has connected to Discord!')


    @bot.event
    async def on_message(message: discord.Message):
        game_log.info(f"received message from {message.author}")
        guild = bot.get_guild(GUILD)
        if message.author == bot.user or message.guild.id != GUILD:
            return

        if isinstance(message.channel, discord.DMChannel):

            msg = message.content.strip()

            if not game_instance.has_submitted_ranking(message.author.name):

                match game_instance.submit_ranking(msg, message.author.name):
                    case 0:
                        await message.channel.send("Ranking received, thank you :) Where do you think you will"
                                                   f" fall in the overall ranking? (1-{game_instance.number_of_players})")
                        game_log.info(f"Accepted ranking from {message.author.display_name}")
                    case 1:
                        await message.channel.send("Your order is not valid, please try again.")
                        game_log.info(f"Rejected ranking from {message.author.display_name}")
                    case 2:
                        await message.channel.send("You are not currently in the game, please join with !join-game")
                        game_log.info(f"Rejected ranking from {message.author.display_name}")

            elif not game_instance.has_submitted_current_round_guess(message.author.name):
                match game_instance.submit_position_guess(msg, message.author.name):
                    case 0:
                        await message.channel.send(f"Guess received, thank you :) The round results will be posted "
                                                   f"in {guild.get_channel(game_instance.channel_id).name} shortly.")
                        game_log.info(f"Accepted position guess from {message.author.display_name}")
                    case 1:
                        await message.channel.send(f"Invalid response. Please submit a single digit in the range"
                                                   f" 1-{game_instance.number_of_players}")
                        game_log.info(f"Accepted position guess from {message.author.display_name}")

            else:
                await message.channel.send(f"You have already submitted all required information for this"
                                           f" round, please wait for the next round to start.")
                game_log.info(f"Rejected DM from {message.author.display_name}")


            if game_instance.received_all_responses and not game_instance.CALCULATING_ROUND_SCORES:
                game_instance.CALCULATING_ROUND_SCORES = True
                game_log.info("Calculating scores for round.")
                game_instance.calculate_rankings()
                output_channel = guild.get_channel(game_instance.channel_id)

                results_message = (f'The results are in!\n\n '
                                   f'This round the question was "{game_instance.current_question}"\n\n'
                                   f'After considering your responses, the overall ranking is as follows:\n\n')

                final_ordering = list(game_instance.current_round_ranking.items())
                final_ordering.sort(key=lambda x: x[1], reverse=False)
                results_message += '\n'.join([f"{x[1]}: {x[0]}" for x in final_ordering]) + '\n\n'

                game_log.info("Ranking for round:"+'|'.join([f"{x[1]}: {x[0]}" for x in final_ordering]))

                results_message += 'You all thought you would be positioned as follows:\n\n'
                results_message += '\n'.join([
                    f"{x[0]}: {x[1]}" for x in game_instance.current_round_position_guesses_entries
                ]) + '.\n\n'

                points_for_round = game_instance.calculate_points()

                results_message += 'This means you each scored points as follows:\n\n'
                results_message += '\n'.join(f"{x[0]}: {x[1]}" for x in points_for_round.items()) + '.\n\n'

                game_log.info("Points for round:" + '|'.join(
                    f"{x[0]}: {x[1]}" for x in points_for_round.items()))

                results_message += 'The overall scores are as now follows:\n\n'
                results_message += '\n'.join([
                    f"{x[0]+1}: {x[1][0]} ({x[1][1]})" for x in enumerate(game_instance.overall_scores)
                ])

                await output_channel.send(results_message)

                if game_instance.CONTINUE:
                    pass

                else:
                    await output_channel.send(f"The game has ended! The winner is "
                                              f"{game_instance.overall_scores[0][0]} with "
                                              f"{game_instance.overall_scores[0][1]} points!")
                    return

        await bot.process_commands(message)

    @bot.command(name='next')
    async def next_round(ctx: commands.Context):
        game_instance.start_new_round()
        game_instance.CALCULATING_ROUND_SCORES = False
        guild = bot.get_guild(GUILD)
        output_channel = guild.get_channel(game_instance.channel_id)
        await output_channel.send(f"The question this round is:\n\n {game_instance.current_question}")
        game_log.info(f"Round Question: {game_instance.current_question}")

        players_in_game_list = '\n'.join([f"{x[0] + 1}: {x[1]}" for x in enumerate(game_instance.player_names)])
        for player in game_instance.players:
            dm_channel = await player.create_dm()
            await dm_channel.send(f"""
            The question this round is:

            {game_instance.current_question}

            Please rank the following players:
            {players_in_game_list}

            Enter your ranking in the format xyz, where x,y,z are either player ids and y can be 0 to indicate no preference for middle positions. 
                                """)


    @bot.command(name='new-game')
    async def reset_game(ctx: commands.Context):
        game_log.info("starting new game")
        game_instance.reset_game(categories=categories, channel_id=ctx.channel.id)



    @bot.command(name='join-game')
    async def join(ctx: commands.Context):
        guild = bot.get_guild(GUILD)
        if ctx.channel.id == game_instance.channel_id:
            game_instance.add_player(ctx.author)
            game_log.info(f"added player {ctx.author.display_name} ({ctx.author.name}) to game")
            game_log.info(f"channel-token: {ctx.channel.id}")
            game_log.info(f'guild_id: {ctx.guild.id}')
            message = (f'added player {ctx.author.display_name} ({ctx.author.name}) to game.'
                       f'\nThere are {game_instance.number_of_players} players in the game ({game_instance.player_names}).')
        else:
            game_log.info(f"Wrong channel id.")
            message = f'This is not the active game channel (wrong channel id)'

        output_channel = guild.get_channel(game_instance.channel_id)
        await output_channel.send(message)



    @bot.command(name='leave-game')
    async def leave(ctx: commands.Context):
        guild = bot.get_guild(GUILD)
        output_channel = guild.get_channel(game_instance.channel_id)
        match game_instance.remove_player(ctx.author):
            case 0:
                await output_channel.send(f'Removed {ctx.author.display_name} ({ctx.author.name}) from game')
            case 1:
                await output_channel.send(f'{ctx.author.display_name} ({ctx.author.name}) will be removed at the end of the round.')


    @bot.command(name='start-game')
    async def start_game(ctx: commands.Context):

        game_log.info(f"Starting new game with players: {','.join(game_instance.player_names)}")

        game_instance.start_new_round()
        players_in_game_list = '\n'.join([f"{x[0] + 1}: {x[1]}" for x in enumerate(game_instance.player_names)])
        for player in game_instance.players:
            dm_channel = await player.create_dm()
            await dm_channel.send(f"""
The question this round is:
    
        {game_instance.current_question}
    
Please rank the following players:
{players_in_game_list}
    
Enter your ranking in the format xyz, where x,y,z are either player ids and y can be 0 to indicate no preference for middle positions. 
                            """)

        game_log.info(f"Round Question: {game_instance.current_question}")
        guild = bot.get_guild(GUILD)
        output_channel = guild.get_channel(game_instance.channel_id)

        await output_channel.send(f"The question this round is:\n\n {game_instance.current_question}")

        pass


    @bot.command(name='final-round')
    async def final_round(ctx: commands.Context):
        game_instance.CONTINUE = False

    @bot.command(name='status')
    async def status(ctx: commands.Context):

        output = f"""
Waiting for rankings from: {[p.nick for p in game_instance.players if not game_instance.has_submitted_ranking(p)]}

Waiting for position guess from: {[p.nick for p in game_instance.players if not game_instance.has_submitted_current_round_guess(p)]}
        """

        await ctx.channel.send(output)


    #################################


    bot.run(TOKEN)
