import discord
from discord_components import Select, SelectOption, Button
from discord.ext import commands
import asyncio
from asyncio import run_coroutine_threadsafe
from urllib import parse, request
import re
import json
import os
from youtube_dl import YoutubeDL

class music_cog(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

        self.is_playing = {}
        self.is_paused = {}
        self.musicQueue = {}
        self.queueIndex = {}

        self.YTDL_OPTIONS = {
            'format': 'bestaudio', 
            'nonplaylist': 'True'
        }

        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

        self.embedBlue = 0x2c76dd
        self.embedRed = 0xdf1141
        self.embedGreen = 0x0eaa51

        self.vc = {}

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            id = int(guild.id)
            self.musicQueue[id] = []
            self.queueIndex[id] = 0
            self.vc[id] = None
            self.is_paused[id] = self.is_playing[id] = False
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        id = int(member.guild.id)
        if member.id != self.bot.user.id and before.channel != None and after.channel != before.channel:
            remainingChannelMembers = before.channel.members
            if len(remainingChannelMembers) == 1 and remainingChannelMembers[0].id == self.bot.user.id and self.vc[id].is_connected():
                self.is_playing[id] = self.is_paused[id] = False
                self.musicQueue[id] = []
                self.queueIndex[id] = 0
                await self.vc[id].disconnect()

    def now_playing_embed(self, ctx, song):
        title = song['title']
        link = song['link']
        thumbnail = song['thumbnail']
        author = ctx.author
        avatar = author.avatar_url

        embed = discord.Embed(
            title = "Now Playing",
            description = f'[{title}]({link})',
            color = self.embedBlue
        )

        embed.set_thumbnail(url = thumbnail)
        embed.set_footer(text=f'Song added by: {str(author)}', icon_url = avatar)
        return embed
    
    def added_song_embed(self, ctx, song):
        title = song['title']
        link = song['link']
        thumbnail = song['thumbnail']
        author = ctx.author
        avatar = author.avatar_url

        embed = discord.Embed(
            title = "Song Added to Queue!",
            description = f'[{title}]({link})',
            color = self.embedRed
        )

        embed.set_thumbnail(url = thumbnail)
        embed.set_footer(text=f'Song added by: {str(author)}', icon_url = avatar)
        return embed
    
    def removed_song_embed(self, ctx, song):
        title = song['title']
        link = song['link']
        thumbnail = song['thumbnail']
        author = ctx.author
        avatar = author.avatar_url

        embed = discord.Embed(
            title = "Song Removed from Queue!",
            description = f'[{title}]({link})',
            color = self.embedRed
        )

        embed.set_thumbnail(url = thumbnail)
        embed.set_footer(text=f'Song removed by: {str(author)}', icon_url = avatar)
        return embed

    async def join_vc(self, ctx, channel):
        id = int(ctx.guild.id)
        if self.vc[id] == None or not self.vc[id].is_connected():
            self.vc[id] = await channel.connect()

            if self.vc[id] == None:
                await ctx.send("Could not connect to the voice channel.")
                return
        else:
            await self.vc[id].move_to(channel)
    
    def get_YT_title(self, videoID):
        params = {"format": "json", "url": "https://www.youtube.com/watch?v=%s" % videoID }
        url = "https://www.youtube.com/oembed"
        queryString = parse.urlencode(params)
        url = url + "?" + queryString
        with request.urlopen(url) as response:
            responseText = response.read()
            data = json.loads(responseText.decode())
            return data['title']


    def search_YT(self, search):
        queryString = parse.urlencode({'search_query': search})
        htmContent = request.urlopen('http://www.youtube.com/results?' + queryString)
        searchResults = re.findall('/watch\?v=(.{11})', htmContent.read().decode())
        return searchResults[0:10]

    def extract_YT(self, url):
        with YoutubeDL(self.YTDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info(url, download = False)
            except:
                return False
        return {
            'link': 'https://www.youtube.com/watch?v=' + url,
            'thumbnail': 'https://i.ytimg.com/vi/' + url + '/hqdefault.jpg?sqp=-oaymwEcCOADEI4CSFXyq4qpAw4IARUAAIhCGAFwAcABBg==&rs=AOn4CLD5uL4xKN-IUfez6KIW_j5y70mlig',
            'source': info['formats'][0]['url'],
            'title': info['title']
        }

    def play_next(self, ctx):
        id = int(ctx.guild.id)
        if not self.is_playing[id]:
            return
        if self.queueIndex[id] + 1 < len(self.musicQueue[id]):
            self.is_playing[id] = True
            self.queueIndex[id] += 1

            song = self.musicQueue[id][self.queueIndex[id]][0]
            message = self.now_playing_embed(ctx, song)
            coro = ctx.send(embed=message)
            fut = run_coroutine_threadsafe(coro, self.bot.loop)
            try:
                fut.result()
            except:
                pass

            self.vc[id].play(discord.FFmpegPCMAudio(song['source'], **self.FFMPEG_OPTIONS), after=lambda e: self.play_next(ctx))
        else:
            self.queueIndex[id] += 1
            self.is_playing = False

    async def play_music(self, ctx):
        id = int(ctx.guild.id)
        if self.queueIndex[id] < len(self.musicQueue[id]):
            self.is_playing[id] = True
            self.is_paused[id] = False
            
            await self.join_vc(ctx, self.musicQueue[id][self.queueIndex[id]][1])

            song = self.musicQueue[id][self.queueIndex[id]][0]
            message = self.now_playing_embed(ctx, song)
            await ctx.send(embed=message)

            self.vc[id].play(discord.FFmpegPCMAudio(song['source'], **self.FFMPEG_OPTIONS), after=lambda e: self.play_next(ctx))
        else:
            await ctx.send("There are no songs in the queue to be played.")
            self.queueIndex[id] +=1
            self.is_playing = False
    
    @ commands.command(name = "play", aliases = ["p"],
        help = """
             Plays (or resumes) the song of a YouTube video. Can take either a url or search terms and starts playing the first result. If no url or terms are specified, then the current song is resumed."""
    )
    async def play(self, ctx, *args):
        search = " ".join(args)
        id = int(ctx.guild.id)
        try:
            userChannel = ctx.author.voice.channel
        except:
            await ctx.send("You need to be connected to a voice channel.")
            return
        if not args:
            if len(self.musicQueue[id]) == 0:
                await ctx.send("There are no songs to be played in the queue")
                return
            elif not self.is_playing[id]:
                if self.musicQueue[id] == None or self.vc[id] == None:
                    await self.play_music(ctx)
                else:
                    self.is_paused[id] = False
                    self.is_playing[id] = True
                    self.vc[id].resume()
            else:
                return
        else:
            song = self.extract_YT(self.search_YT(search)[0])
            if type(song) == type(True):
                await ctx.send("Could not download the song. Incorrect format; try using other keywords.")
            else:
                self.musicQueue[id].append([song, userChannel])
                if not self.is_playing[id]:
                    await self.play_music(ctx)
                else:
                    message = self.added_song_embed(ctx, song)
                    await ctx.send(embed=message)

    @ commands.command(name = "add", aliases = ["a"],
        help = """
             Adds a song to the queue. Can take either a url or search terms and starts playing the first result."""
    )
    async def add(self, ctx, *args):
        search = " ".join(args)
        try:
            userChannel = ctx.author.voice.channel
        except:
            await ctx.send("You need to be in a voice channel.")
            return
        if not args:
            await ctx.send("You need to specify a song to add.")
        else:
            song = self.extract_YT(self.search_YT(search)[0])
            if type(song) == type(False):
                await ctx.send("Could not download the song. Incorrect format; try using other keywords.")
                return
            else:
                self.musicQueue[ctx.guild.id].append([song, userChannel])
                message = self.added_song_embed(ctx, song)
                await ctx.send(embed=message)

    @ commands.command(name = "remove", aliases = ["rm"],
        help = """
             Removes the last added song from the queue."""
    )
    async def remove(self, ctx):
        id = int(ctx.guild.id)
        if self.musicQueue[id] != []:
            song = self.musicQueue[id][-1][0]
            removeSongEmbed = self.removed_song_embed(ctx, song)
            await ctx.send(embed=removeSongEmbed)
        else:
            await ctx.send("There are no songs to be removed in the queue.")
        self.musicQueue[id] = self.musicQueue[id][:-1]
        if self.musicQueue[id] == []:
            if self.vc[id] != None and self.is_playing[id]:
                self.is_playing[id] = self.is_paused[id] = False
                await self.vc[id].disconnect()
                self.vc[id] = None
            self.queueIndex[id] = 0
        elif self.queueIndex[id] == len(self.musicQueue[id]) and self.vc[id] != None and self.vc[id]:
            self.vc[id].pause()
            self.queueIndex[id] -=1
            await self.play_music(ctx)
    
    @ commands.command(name = "previous", aliases = ["prev", "pr"],
        help = "Plays the previous song from the queue. Repeats the song if it's the first song in the queue."
    )
    async def previous(self, ctx):
        id = int(ctx.guild.id)
        if self.vc[id] == None:
            await ctx.send("You need to be in a voice channel.")
        elif self.queueIndex[id] <= 0:
            await ctx.send("There is no previous song in the queue. Replaying current song.")
            self.vc[id].pause()
            await self.play_music(ctx)
        elif self.vc[id] != None and self.vc[id]:
            self.vc[id].pause()
            self.queueIndex[id] -=1
            await self.play_music(ctx)

    @ commands.command(name = "skip", aliases = ["next", "sk"], help = "Plays the next song from the queue. Repeats the song if it's the last song in the queue.")
    async def skip(self, ctx):
        id = int(ctx.guild.id)
        if self.vc[id] == None:
            await ctx.send("You need to be in a voice channel.")
        elif self.queueIndex[id] >= len(self.musicQueue[id])-1: 
            await ctx.send("There is no next song in the queue. Replaying current song.")
            self.vc[id].pause()
            await self.play_music(ctx)
        elif self.vc[id] != None and self.vc[id]:
            self.vc[id].pause()
            self.queueIndex[id] +=1
            await self.play_music(ctx)

    @ commands.command(name = "queue", aliases = ["list", "q"], help = "Lists the audios in the queue, including the current playing song and upto the next 10 songs")
    async def queue(self, ctx):
        id = int(ctx.guild.id)
        returnValue = ""
        if self.musicQueue[id] == []:
            await ctx.send("There are no songs in the queue.")
            return
        
        for i in range(self.queueIndex[id], len(self.musicQueue[id])):
            upNextSongs = len(self.musicQueue[id]) - self.queueIndex[id]
            if i > 5 + upNextSongs:
                break
            returnIndex = i - self.queueIndex[id]
            if returnIndex == 0:
                returnIndex = "Playing "
            elif returnIndex == 1:
                returnIndex = "Next: \n1"
            returnValue += f"{returnIndex} - [{self.musicQueue[id][i][0]['title']}]({self.musicQueue[id][i][0]['link']})\n"

            if returnValue == "":
                await ctx.send("There are no songs in the queue.")
                return

        queue = discord.Embed(
            title = "Current Queue",
            description = returnValue,
            coloud = self.embedGreen
        )
        await ctx.send(embed=queue)

    @ commands.command(name = "clear", aliases = ["cl"], help = "Clears the queue.")
    async def clear(self, ctx):
        id = int(ctx.guild.id)
        if self.vc[id] != None and self.is_playing[id]:
            self.is_playing[id] = self.is_paused[id] = False
            self.vc[id].stop()
        if self.musicQueue[id] != []:
            await ctx.send("The music queue has been cleared.")
            self.musicQueue[id] = []
        self.queueIndex[id]=0

    @ commands.command(name = "search", aliases = ["find", "sr"], help = "Select a song from a list of 10 matching Youtube videos. Can take a url or search terms.")
    async def search(self, ctx, *args):
        search = " ".join(args)
        songNames = []
        selectionOptions = []
        embedText = ""

        if not args:
            await ctx.send("You must specify search terms.")
            return
        try:
            userChannel = ctx.author.voice.channel
        except:
            await ctx.send("You need to be in a voice channel.")
            return
        
        await ctx.send("Fetching search results...")

        songTokens = self.search_YT(search)
        for i, token in enumerate(songTokens):
            url = 'https://www.youtube.com/watch?v=' + token
            name = self.get_YT_title(token)
            songNames.append(name)
            embedText  += f"{i+1} - [{name}]({url})\n"

        for i, title in enumerate(songNames):
            selectionOptions.append(SelectOption(label = f"{i+1} - {title[:95]}", value = i)) 
            
        searchResults = discord.Embed(title = "Search Results", description = embedText, colour = self.embedRed)
        selectionComponents = [Select ( placeholder = "Select an option", options= selectionOptions), Button (label = "Cancel", custom_id = "Canel", style = 4)]
        message = await ctx.send(embed = searchResults, components = selectionComponents)

        try:
            tasks = [ 
                asyncio.create_task(self.bot.wait_for("button_click", timeout = 60.0, check = None), name= "button"),
                asyncio.create_task(self.bot.wait_for("select_option", timeout = 60.0, check = None), name = "select")
            ]
            done, pending = await asyncio.wait(tasks, return_when= asyncio.FIRST_COMPLETED)
            finished = list(done)[0]

            for task in pending:
                try:
                    task.cancel()
                except asyncio.CancelledError:
                    pass
            
            if finished == None:
                searchResults.title = "Search Failed"
                searchResults.description = ""
                await message.delete()
                await ctx.send(embed=searchResults)
                return

            action = finished.get_name()
            if action == "button":
                searchResults.title = "Search Failed"
                searchResults.description = ""
                await message.delete()
                await ctx.send(embed=searchResults)
            elif action == "select":
                result = finished.result()
                chosenIndex = int(result.values[0])
                songRef = self.extract_YT(songTokens[chosenIndex])
                if type(songRef) == type(True):
                    await ctx.send("Could not download the song. Incorrect format, try different keywords")
                    return
                embedResponse = discord.Embed(
                    title = f"Option #{chosenIndex +1} selected",
                    description = f"[{songRef['title']}]({songRef['link']}) added to the queue!",
                    colour = self.embedRed
                )
                embedResponse.set_thumbnail(url = songRef['thumbnail'])
                await message.delete()
                await ctx.send(embed=embedResponse)
                self.musicQueue[ctx.guild.id].append([songRef, userChannel])
        except: 
            searchResults.title = "Search Failed"
            searchResults.description = ""
            await message.delete()
            await ctx.send(embed=searchResults)
            
    @ commands.command(name = "pause", aliases = ["pa"], help = "Pauses the current playing song.")
    async def pause(self, ctx):
        id = int(ctx.guild.id)
        if not self.vc[id]:
            await ctx.send("There is no song to be paused at the moment.")
        elif self.is_playing[id]:
            await ctx.send("The song is now paused!")
            self.is_playing[id] = False
            self.is_paused[id] = True
            self.vc[id].pause()

    @ commands.command(name = "resume", aliases = ["r"], help = "Resumes the paused song.")
    async def resume(self, ctx):
        id = int(ctx.guild.id)
        if not self.vc[id]:
            await ctx.send("There is no song to be played at the moment.")
        if self.is_paused[id]:
            await ctx.send("The song is now playing!")
            self.is_playing[id] = True
            self.is_paused[id] = False
            self.vc[id].resume()

    @ commands.command(name = "join", aliases = ["j"], help = "Joins the voice channel.")
    async def join(self, ctx):
        if ctx.author.voice:
            userChannel = ctx.author.voice.channel
            await self.join_vc(ctx, userChannel)
            await ctx.send(f'Sirius has joined "{userChannel}"')
        else:
            await ctx.send("You need to be connected to a voice channel.")
    
    @ commands.command(name = "leave", aliases = ["l"], help = "Leaves the voice channel")
    async def leave(self, ctx):
        id = int(ctx.guild.id)
        self.is_playing[id] = self.is_paused[id] = False
        self.musicQueue[id] = []
        self.queueIndex[id] = 0
        if self.vc[id] != None:
            await ctx.send("Sirius has left the voice channel")
            await self.vc[id].disconnect()
            self.vc[id] = None