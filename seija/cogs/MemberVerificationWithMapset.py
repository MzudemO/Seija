import sqlite3
from discord.ext import commands
from discord.utils import escape_markdown
from seija.reusables import exceptions
from seija.reusables import verification as verification_reusables
from seija.embeds import oldembeds as osuembed
import re


class MemberVerificationWithMapset(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        conn = sqlite3.connect(self.bot.database_file)
        c = conn.cursor()
        self.verify_channel_list = tuple(c.execute("SELECT channel_id, guild_id FROM channels WHERE setting = ?",
                                                   ["verify"]))
        conn.close()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id == self.bot.user.id:
            return

        for verify_channel_id in self.verify_channel_list:
            if message.channel.id != int(verify_channel_id[0]):
                continue

            if "https://osu.ppy.sh/beatmapsets/" in message.content:
                mapset_id = self.grab_osu_mapset_id_from_text(message.content)
                await self.mapset_id_verification(message.channel, message.author, mapset_id)
                return

            return

    async def mapset_id_verification(self, channel, member, mapset_id):
        try:
            mapset = await self.bot.osu.get_beatmapset(s=mapset_id)
        except Exception as e:
            await channel.send("i am having issues connecting to osu servers to verify you. "
                               "try again later or wait for a manager to help",
                               embed=await exceptions.embed_exception(e))
            return

        if not mapset:
            await channel.send("verification failure, I can't find any map with that link")
            return

        try:
            is_not_restricted = await self.bot.osu.get_user(u=mapset.creator_id)
            if is_not_restricted:
                await channel.send("verification failure, "
                                   "verification through mapset is reserved for restricted users only. "
                                   "this is like this to reduce confusion and errors")
                return
        except:
            pass

        # this won't work on restricted users, thanks peppy.
        # member_mapsets = await self.bot.osu.get_beatmapsets(u=str(mapset.creator_id))
        # ranked_amount = await self.count_ranked_beatmapsets(member_mapsets)
        ranked_amount = 0
        role = await verification_reusables.get_role_based_on_reputation(self, member.guild, ranked_amount)

        async with self.bot.db.execute("SELECT osu_id FROM users WHERE user_id = ?", [int(member.id)]) as cursor:
            already_linked_to = await cursor.fetchone()
        if already_linked_to:
            if int(mapset.creator_id) != int(already_linked_to[0]):
                await channel.send(f"{member.mention} it seems like your discord account is already in my database "
                                   f"and is linked to <https://osu.ppy.sh/users/{already_linked_to[0]}>")
                return
            else:
                try:
                    await member.add_roles(role)
                    await member.edit(nick=mapset.creator)
                except:
                    pass
                await channel.send(content=f"{member.mention} i already know lol. here, have some roles")
                return

        async with self.bot.db.execute("SELECT user_id FROM users WHERE osu_id = ?",
                                       [int(mapset.creator_id)]) as cursor:
            check_if_new_discord_account = await cursor.fetchone()
        if check_if_new_discord_account:
            if int(check_if_new_discord_account[0]) != int(member.id):
                old_user_id = check_if_new_discord_account[0]
                await channel.send(f"this osu account is already linked to <@{old_user_id}> in my database. "
                                   "if there's a problem, for example, you got a new discord account, ping kyuunex.")
                return

        try:
            await member.add_roles(role)
            await member.edit(nick=mapset.creator)
        except:
            pass

        embed = await osuembed.beatmapset(mapset)
        await self.bot.db.execute("DELETE FROM users WHERE user_id = ?", [int(member.id)])
        await self.bot.db.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?,?)",
                                  [int(member.id), int(mapset.creator_id), str(mapset.creator), 0, 0, None,
                                   int(ranked_amount), 0, 0, 0])
        await self.bot.db.commit()

        await channel.send(content=f"`Verified through mapset: {escape_markdown(member.name)}` \n"
                                   f"You should also read the rules if you haven't already.", embed=embed)

    def grab_osu_mapset_id_from_text(self, text):
        """
        Gets the osu! mapset ID from a mapset URL.

        Parameters
        ----------
        text : String
            osu! mapset URL.

        Returns
        -------
        String
            MapsetID, or None if no match
        """

        pattern = re.compile(r"""osu                    # only new site
                                 \.ppy\.sh\/            # domain
                                 (?:s|beatmapsets)\/    # valid set links
                                 (\d+)                  # mapset ID (1 or more digits)
                                 .*$                    # allow any trailing chars
                            """, re.X)
        matches = re.search(pattern, text) 
        # group 0 returns the full string if matched, 1..n return capture groups
        return matches and matches.group(1)


def setup(bot):
    bot.add_cog(MemberVerificationWithMapset(bot))
