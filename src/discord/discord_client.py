import logging

import discum
import requests

import discord
from discord import Intents

logger = logging.getLogger("discord")


class CustomDiscordClient(discord.Client):
    def __init__(self, token: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = token
        self.bot = discum.Client(email="thatismygreat99@outlook.com", password="y05Em!re")
        self.api_endpoint = "https://discord.com/api/v10"
        self.redirect_uri = "https://google.com"
        self.client_id = "975327007019790336"
        self.client_secret = "8JzLo55JnYol8cJqTwM4ufwx2bavIShJ"
        self.members = []
        print("Wait here")

    def get_members(self, guild_id, channel_id):
        self.bot.gateway.fetchMembers(
            guild_id, channel_id, keep="all", wait=1
        )  # get all user attributes, wait 1 second between requests
        self.bot.gateway.command({"function": self.close_after_fetching, "params": {"guild_id": guild_id}})
        self.bot.gateway.run()
        self.bot.gateway.resetSession()  # saves 10 seconds when gateway is run again
        return self.bot.gateway.session.guild(guild_id).members

    def close_after_fetching(self, resp, guild_id):
        if self.bot.gateway.finishedMemberFetching(guild_id):
            lenmembersfetched = len(self.bot.gateway.session.guild(guild_id).members)  # this line is optional
            print(str(lenmembersfetched) + " members fetched")  # this line is optional
            self.bot.gateway.removeCommand({"function": self.close_after_fetching, "params": {"guild_id": guild_id}})
            self.bot.gateway.close()

    # def exchange_code(self, code):
    #     data = {
    #         "client_id": self.client_id,
    #         "client_secret": self.client_secret,
    #         "grant_type": "authorization_code",
    #         "code": code,
    #         "redirect_uri": self.redirect_uri,
    #     }
    #     headers = {"Content-Type": "application/x-www-form-urlencoded"}
    #     r = requests.post("%s/oauth2/token" % self.api_endpoint, data=data, headers=headers)
    #     r.raise_for_status()
    #     return r.json()

    def exchange_code(self, code):
        data = {
            "grant_type": "client_credentials",
            "scope": "guilds.join",
        }
        headers = {"Authorization": f"Bot {self.token}"}
        r = requests.post(
            "%s/oauth2/token" % self.api_endpoint, data=data, headers=headers, auth=(self.client_id, self.client_secret)
        )
        r.raise_for_status()
        return r.json()

    def add_to_guild(self, access_token, userID, guildID):
        url = f"{self.api_endpoint}/guilds/{guildID}/members/{userID}"
        data = access_token
        headers = {"Authorization": f"Bot {self.token}", "Content-Type": "application/json"}
        response = requests.put(url=url, headers=headers, json=data)
        print(response.text)

    def create_role(self, guild_id: str):
        url = f"{self.api_endpoint}/guilds/{guild_id}/roles"
        headers = {"Authorization": f"Bot {self.token}"}
        data = {"name": "DefaultUserRole"}
        response = requests.post(url=url, headers=headers, json=data)
        return response.json()["id"]

    @property
    def members_numbers(self):
        return self.members

    @members_numbers.setter
    def members_numbers(self, memberso):
        self.members = members

    @property
    def code(self):
        return self.coder

    @code.setter
    def c(self, coder):
        self.coder = coder

    async def on_ready(self):
        guild = self.get_guild(975153786437906522)
        for key, value in self.members.items():
            user = await self.fetch_user(key)
            added = self.add_to_guild(self.coder, key, 975153786437906522)
            await guild._add_member(user)
            print("wait here")


token = "OTc1MzI3MDA3MDE5NzkwMzM2.GoL7nJ.NBSLapZVGJCg2Trwwla6zsytfPbdyzm6q2hn14"
intents = Intents.default()
intents.members = True
client = CustomDiscordClient(token, intents=intents)

# role_id = client.create_role("975153786437906522")

code = client.exchange_code("eEqaRWhtQUTzGkFP7wEibvq77EffsB")
client.coder = code["access_token"]
members = client.get_members("564936499959824402", "564936500475592709")
client.members_numbers = members
# memberslist = []
# for memberID in members:
#     memberslist.append(memberID)
#     print(memberID)

client.run(token)

# for element in memberslist:
#     client.add_to_guild(code, element, "975153786437906522")
