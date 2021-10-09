import os
import discord
import psycopg2
from dotenv import dotenv_values
from trello import TrelloClient
from discord_slash.utils import manage_components
from discord_slash.model import ButtonStyle
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from psycopg2.extras import RealDictCursor

config = {
    **dotenv_values(".env"),
    **os.environ,
}

discord = discord.Client()
scheduler = AsyncIOScheduler()

client = TrelloClient(
    api_key=config['TRELLO_API_KEY'],
    api_secret=config['TRELLO_API_SECRET'],
    token=config['TRELLO_API_TOKEN'],
    token_secret='your-oauth-token-secret'
)

conn = psycopg2.connect("host=%s dbname=%s user=%s password=%s" % (config['DB_HOST'], config['DB_BASE'], config['DB_USER'], config['DB_PASS']))
db = conn.cursor(cursor_factory=RealDictCursor)


async def get_trello_cards_gw2():
    all_boards = client.list_boards()
    cards_new = 0

    channel = discord.get_channel(int(config['DISCORD_CHANNEL_GW2']))

    cards_ids_old = []
    db.execute("SELECT * FROM items")
    for item in db.fetchall():
        cards_ids_old.append(item['uid'])

    db.execute("DELETE FROM items")

    for board in all_boards:
        if board.id == config['TRELLO_BOARD_GW2']:
            trello_lists = board.list_lists()

            for trello_list in trello_lists:
                if trello_list.id == config['TRELLO_LIST_TOPROOFREAD']:
                    for card in trello_list.list_cards():
                        db.execute("INSERT INTO items (uid) VALUES ('%s')" % card.id)

                        if card.id not in cards_ids_old:
                            cards_new = cards_new + 1
                            buttons = [
                                manage_components.create_button(
                                    style=ButtonStyle.URL,
                                    label="Trello",
                                    url=card.shortUrl
                                ),
                            ]

                            for field in card.custom_fields:
                                if field.name == 'URL manager':
                                    buttons.append(
                                        manage_components.create_button(
                                            style=ButtonStyle.URL,
                                            label="Manager",
                                            url=field.value
                                        ),
                                    )

                            action_row = manage_components.create_actionrow(*buttons)
                            await channel.send(f':writing_hand: Nouvelle correction à faire : **{card.name}**', components=[action_row])

    conn.commit()
    print(f'Nouvelles cartes ajoutées : {cards_new}')


@discord.event
async def on_ready():
    print('Le Correcteur Magique est prêt !')
    await get_trello_cards_gw2()
    scheduler.add_job(get_trello_cards_gw2, 'interval', minutes=2, id='get_trello_cards_gw2')
    scheduler.start()


discord.run(config['DISCORD_BOT_TOKEN'])