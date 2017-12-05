#-*-coding:utf-8-*-
import os
import sys
import time
import shlex
import shutil
import inspect
import aiohttp
import discord
import asyncio
import traceback

from discord import utils
from discord.object import Object
from discord.enums import ChannelType
from discord.voice_client import VoiceClient
from discord.ext.commands.bot import _get_variable

from io import BytesIO
from functools import wraps
from textwrap import dedent
from datetime import timedelta
from datetime import datetime
from random import choice, shuffle
from collections import defaultdict

from musicbot.playlist import Playlist
from musicbot.player import MusicPlayer
from musicbot.config import Config, ConfigDefaults
from musicbot.permissions import Permissions, PermissionsDefaults
from musicbot.utils import load_file, write_file, sane_round_int

from . import exceptions
from .opus_loader import load_opus_lib
from .constants import VERSION as BOTVERSION
from .constants import DISCORD_MSG_CHAR_LIMIT, AUDIO_CACHE_PATH

from musicbot.fitness_classes import Database,Exercise_Recorder,Plotter,BMI_Calculator
from pytz import timezone
import json

load_opus_lib()

class Response:
    def __init__(self, content, reply=False, delete_after=0):
        self.content = content
        self.reply = reply
        self.delete_after = delete_after


class MusicBot(discord.Client):
    def __init__(self, config_file=ConfigDefaults.options_file, perms_file=PermissionsDefaults.perms_file):

        self.locks = defaultdict(asyncio.Lock)

        self.config = Config(config_file)
        self.permissions = Permissions(perms_file, grant_all=[self.config.owner_id])

        self.blacklist = set(load_file(self.config.blacklist_file))
        
        self.exit_signal = None
        self.init_ok = False
        self.cached_client_id = None

        #################################################################################
        self.database = Database("accounts")
        self.exercises = Exercise_Recorder(self.database)
        self.plotter = Plotter(self.database)
        self.bmi_calculator = BMI_Calculator(self.database)
        #################################################################################
        # TODO: Do these properly
        ssd_defaults = {'last_np_msg': None, 'auto_paused': False}
        self.server_specific_data = defaultdict(lambda: dict(ssd_defaults))

        super().__init__()
        self.aiosession = aiohttp.ClientSession(loop=self.loop)
        self.http.user_agent += ' MusicBot/%s' % BOTVERSION
    # TODO: Add some sort of `denied` argument for a message to send when someone else tries to use it
    def owner_only(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Only allow the owner to use these commands
            orig_msg = _get_variable('message')

            if not orig_msg or orig_msg.author.id == self.config.owner_id:
                return await func(self, *args, **kwargs)
            else:
                raise exceptions.PermissionsError("only the owner can use this command", expire_in=30)

        return wrapper

    @staticmethod
    def _fixg(x, dp=2):
        return ('{:.%sf}' % dp).format(x).rstrip('0').rstrip('.')

    def _get_owner(self, voice=False):
        if voice:
            for server in self.servers:
                for channel in server.channels:
                    for m in channel.voice_members:
                        if m.id == self.config.owner_id:
                            return m
        else:
            return discord.utils.find(lambda m: m.id == self.config.owner_id, self.get_all_members())


    async def _wait_delete_msg(self, message, after):
        await asyncio.sleep(after)
        await self.safe_delete_message(message)

    async def update_now_playing(self, entry=None, is_paused=False):
        game = None

        if self.user.bot:
            activeplayers = sum(1 for p in self.players.values() if p.is_playing)
            if activeplayers > 1:
                game = discord.Game(name="music on %s servers" % activeplayers)
                entry = None

            elif activeplayers == 1:
                player = discord.utils.get(self.players.values(), is_playing=True)
                entry = player.current_entry

        if entry:
            prefix = u'\u275A\u275A ' if is_paused else ''

            name = u'{}{}'.format(prefix, entry.title)[:128]
            game = discord.Game(name=name)
            
        await self.change_presence(game=game)


    async def safe_send_message(self, dest, content, *, tts=False, expire_in=0, also_delete=None, quiet=False):
        msg = None
        try:
            msg = await self.send_message(dest, content, tts=tts)

            if msg and expire_in:
                asyncio.ensure_future(self._wait_delete_msg(msg, expire_in))

            if also_delete and isinstance(also_delete, discord.Message):
                asyncio.ensure_future(self._wait_delete_msg(also_delete, expire_in))

        except discord.Forbidden:
            if not quiet:
                self.safe_print("Warning: Cannot send message to %s, no permission" % dest.name)

        except discord.NotFound:
            if not quiet:
                self.safe_print("Warning: Cannot send message to %s, invalid channel?" % dest.name)

        return msg

    async def safe_delete_message(self, message, *, quiet=False):
        try:
            return await self.delete_message(message)

        except discord.Forbidden:
            if not quiet:
                self.safe_print("Warning: Cannot delete message \"%s\", no permission" % message.clean_content)

        except discord.NotFound:
            if not quiet:
                self.safe_print("Warning: Cannot delete message \"%s\", message not found" % message.clean_content)

    async def safe_edit_message(self, message, new, *, send_if_fail=False, quiet=False):
        try:
            return await self.edit_message(message, new)

        except discord.NotFound:
            if not quiet:
                self.safe_print("Warning: Cannot edit message \"%s\", message not found" % message.clean_content)
            if send_if_fail:
                if not quiet:
                    print("Sending instead")
                return await self.safe_send_message(message.channel, new)

    def safe_print(self, content, *, end='\n', flush=True):
        sys.stdout.buffer.write((content + end).encode('utf-8', 'replace'))
        if flush: sys.stdout.flush()

    async def send_typing(self, destination):
        try:
            return await super().send_typing(destination)
        except discord.Forbidden:
            if self.config.debug_mode:
                print("Could not send typing to %s, no permssion" % destination)

    def _cleanup(self):
        try:
            self.loop.run_until_complete(self.logout())
        except: # Can be ignored
            pass

        pending = asyncio.Task.all_tasks()
        gathered = asyncio.gather(*pending)

        try:
            gathered.cancel()
            self.loop.run_until_complete(gathered)
            gathered.exception()
        except: # Can be ignored
            pass
        
    # noinspection PyMethodOverriding
    def run(self):
        try:
            self.loop.create_task(self.reminder_loop())
            self.loop.run_until_complete(self.start(*self.config.auth))
        except discord.errors.LoginFailure:
            # Add if token, else
            raise exceptions.HelpfulError(
                "Bot cannot login, bad credentials.",
                "Fix your Email or Password or Token in the options file.  "
                "Remember that each field should be on their own line.")

        finally:
            try:
                self._cleanup()
            except Exception as e:
                print("Error in cleanup:", e)

            self.loop.close()
            if self.exit_signal:
                raise self.exit_signal

    async def update_stat_message(self):
        game = discord.Game(name="Type !help for commands")
        await self.change_presence(game=game)
        
    async def logout(self):
        return await super().logout()

    async def on_error(self, event, *args, **kwargs):
        ex_type, ex, stack = sys.exc_info()

        if ex_type == exceptions.HelpfulError:
            print("Exception in", event)
            print(ex.message)

            await asyncio.sleep(2)  # don't ask
            await self.logout()

        elif issubclass(ex_type, exceptions.Signal):
            self.exit_signal = ex_type
            await self.logout()

        else:
            traceback.print_exc()

    async def on_ready(self):
        print('\rConnected!  Musicbot v%s\n' % BOTVERSION)

        if self.config.owner_id == self.user.id:
            raise exceptions.HelpfulError(
                "Your OwnerID is incorrect or you've used the wrong credentials.",

                "The bot needs its own account to function.  "
                "The OwnerID is the id of the owner, not the bot.  "
                "Figure out which one is which and use the correct information.")

        self.init_ok = True

        self.safe_print("Bot:   %s/%s#%s" % (self.user.id, self.user.name, self.user.discriminator))

        owner = self._get_owner(voice=True) or self._get_owner()
        if owner and self.servers:
            self.safe_print("Owner: %s/%s#%s\n" % (owner.id, owner.name, owner.discriminator))

            print('Server List:')
            [self.safe_print(' - ' + s.name) for s in self.servers]

        elif self.servers:
            print("Owner could not be found on any server (id: %s)\n" % self.config.owner_id)

            print('Server List:')
            [self.safe_print(' - ' + s.name) for s in self.servers]

        else:
            print("Owner unknown, bot is not on any servers.")
            if self.user.bot:
                print("\nTo make the bot join a server, paste this link in your browser.")
                print("Note: You should be logged into your main account and have \n"
                      "manage server permissions on the server you want the bot to join.\n")
                print("    " + await self.generate_invite_link())

        print()

        if self.config.bound_channels:
            chlist = set(self.get_channel(i) for i in self.config.bound_channels if i)
            chlist.discard(None)
            invalids = set()

            invalids.update(c for c in chlist if c.type == discord.ChannelType.voice)
            chlist.difference_update(invalids)
            self.config.bound_channels.difference_update(invalids)

            print("Bound to text channels:")
            [self.safe_print(' - %s/%s' % (ch.server.name.strip(), ch.name.strip())) for ch in chlist if ch]

            if invalids and self.config.debug_mode:
                print("\nNot binding to voice channels:")
                [self.safe_print(' - %s/%s' % (ch.server.name.strip(), ch.name.strip())) for ch in invalids if ch]

            print()

        else:
            print("Not bound to any text channels")

        print()
        print("Options:")

        self.safe_print("  Command prefix: " + self.config.command_prefix)
        print("  Delete Messages: " + ['Disabled', 'Enabled'][self.config.delete_messages])
        if self.config.delete_messages:
            print("    Delete Invoking: " + ['Disabled', 'Enabled'][self.config.delete_invoking])
        print("  Debug Mode: " + ['Disabled', 'Enabled'][self.config.debug_mode])
        print()


    async def cmd_help(self, command=None):
        """
        Usage:
            {command_prefix}help [command]

        Prints a help message.
        If a command is specified, it prints a help message for that command.
        Otherwise, it lists the available commands.
        """
        await self.update_stat_message()
        if command:
            cmd = getattr(self, 'cmd_' + command, None)
            if cmd:
                return Response(
                    "```\n{}```".format(
                        dedent(cmd.__doc__),
                        command_prefix=self.config.command_prefix
                    ),
                    delete_after=60
                )
            else:
                return Response("No such command", delete_after=10)

        else:
            helpmsg = "**Commands**\n```"
            commands = []

            for att in dir(self):
                if att.startswith('cmd_') and att != 'cmd_help':
                    command_name = att.replace('cmd_', '').lower()
                    commands.append("{}{}".format(self.config.command_prefix, command_name))

            helpmsg += ", ".join(commands)
            helpmsg += "```"

            return Response(helpmsg, reply=True, delete_after=60)

    async def _cmd_id(self, author, user_mentions):
        """
        Usage:
            {command_prefix}id [@user]

        Tells the user their id or the id of another user.
        """
        if not user_mentions:
            return Response('your id is `%s`' % author.id, reply=True, delete_after=35)
        else:
            usr = user_mentions[0]
            return Response("%s's id is `%s`" % (usr.name, usr.id), reply=True, delete_after=35)

    async def _cmd_listids(self, server, author, leftover_args, cat='all'):
        """
        Usage:
            {command_prefix}listids [categories]

        Lists the ids for various things.  Categories are:
           all, users, roles, channels
        """

        cats = ['channels', 'roles', 'users']

        if cat not in cats and cat != 'all':
            return Response(
                "Valid categories: " + ' '.join(['`%s`' % c for c in cats]),
                reply=True,
                delete_after=25
            )

        if cat == 'all':
            requested_cats = cats
        else:
            requested_cats = [cat] + [c.strip(',') for c in leftover_args]

        data = ['Your ID: %s' % author.id]

        for cur_cat in requested_cats:
            rawudata = None

            if cur_cat == 'users':
                data.append("\nUser IDs:")
                rawudata = ['%s #%s: %s' % (m.name, m.discriminator, m.id) for m in server.members]

            elif cur_cat == 'roles':
                data.append("\nRole IDs:")
                rawudata = ['%s: %s' % (r.name, r.id) for r in server.roles]

            elif cur_cat == 'channels':
                data.append("\nText Channel IDs:")
                tchans = [c for c in server.channels if c.type == discord.ChannelType.text]
                rawudata = ['%s: %s' % (c.name, c.id) for c in tchans]

                rawudata.append("\nVoice Channel IDs:")
                vchans = [c for c in server.channels if c.type == discord.ChannelType.voice]
                rawudata.extend('%s: %s' % (c.name, c.id) for c in vchans)

            if rawudata:
                data.extend(rawudata)

        with BytesIO() as sdata:
            sdata.writelines(d.encode('utf8') + b'\n' for d in data)
            sdata.seek(0)

            # TODO: Fix naming (Discord20API-ids.txt)
            await self.send_file(author, sdata, filename='%s-ids-%s.txt' % (server.name.replace(' ', '_'), cat))

        return Response(":mailbox_with_mail:", delete_after=20)

    async def cmd_restart(self, channel):
        await self.safe_send_message(channel, ":ok_hand:")
        raise exceptions.RestartSignal

    async def cmd_shutdown(self, channel):
        await self.safe_send_message(channel, ":wave:")
        raise exceptions.TerminateSignal

####################################################################################
    async def cmd_history(self,channel, author, message, leftover_args):
        username =  author.name +"#"+author.discriminator
        if username not in self.database.data_list["users"].keys():
            self.database.add_user(username,author.id)
        check_date = datetime.now(timezone('US/Pacific'))
        check_string = str(check_date.month)+"/"+str(check_date.day)+"/"+str(check_date.year)
        latest = 14
        if leftover_args:
            try:
                latest = int(leftover_args[0])
            except:
                print("Nope")
        latest_history = self.plotter.get_log_history_string(username,latest)
        return Response('Log History Past '+str(latest)+' Days:\n'+latest_history, reply=True, delete_after=0)

    async def cmd_log(self,channel, author, message, leftover_args):
        await self.update_stat_message()
        username =  author.name +"#"+author.discriminator
        if username not in self.database.data_list["users"].keys():
            self.database.add_user(username,author.id)
        def argcheck():
            if not leftover_args:
                check_date = datetime.now(timezone('US/Pacific'))
                check_string = str(check_date.month)+"/"+str(check_date.day)+"/"+str(check_date.year)
                latest_log = self.plotter.get_log_by_date(username,check_string)
                if not latest_log:
                    raise exceptions.CommandError("No log inputted for today! \n\nUse !log <category> <number>, !emoji, or !routine to record log")
                else:
                    raise exceptions.CommandError("Latest Log:\n"+str(self.plotter.get_last_log_string(username,check_string))+"\n"+self.exercises.routines_today_string(username)+"\n\nUse !log <category> <number>, !emoji, or !routine to record log")

        argcheck()
        self.plotter.set_category_today(username,leftover_args[0],float(leftover_args[1]))
        date_now = str(datetime.now(timezone('US/Pacific')).month)+"/"+str(datetime.now(timezone('US/Pacific')).day)+"/"+str(datetime.now(timezone('US/Pacific')).year)
        if leftover_args[0] == "weight":
            self.bmi_calculator.set_weight(username,float(leftover_args[1]))
        return Response('Sucessfully modified todays log!\n    Date: '+date_now+'\n    Category: '+leftover_args[0]+"\n    value: "+str(float(leftover_args[1])), reply=True, delete_after=0)

    async def cmd_chart(self, channel, author, message, leftover_args):
        await self.update_stat_message()
        username =  author.name +"#"+author.discriminator
        if username not in self.database.data_list["users"].keys():
            self.database.add_user(username,author.id)
        def argcheck():
            if not leftover_args:
                raise exceptions.CommandError("Enter Chart Category: !chart <category>")

        argcheck()
        latest = 1
        if len(leftover_args)==1:
            latest = 10
        else:
            latest = int(leftover_args[1])
        if self.plotter.generate_chart(username, leftover_args[0],latest) == "Empty List":
            return Response("No data to Chart for Category: "+leftover_args[0], reply=True, delete_after=0)
        else:
            await self.send_file(channel,"plot_graphs/"+username+"_"+leftover_args[0]+"_graph.png")

    async def cmd_height(self, author, channel, message, leftover_args):
        await self.update_stat_message()
        username =  author.name +"#"+author.discriminator
        if username not in self.database.data_list["users"].keys():
            self.database.add_user(username,author.id)
        def argcheck():
            if not leftover_args:
                raise exceptions.CommandError("Enter height with {'} seperator:\n!height 1'2")

        argcheck()
        self.bmi_calculator.set_height(username, leftover_args[0])
        return Response('Sucessfully modified user height!\n    Height: '+leftover_args[0], reply=True, delete_after=0)

        
    async def cmd_bmi(self, author, channel, message):
        await self.update_stat_message()
        username =  author.name +"#"+author.discriminator
        if username not in self.database.data_list["users"].keys():
            self.database.add_user(username,author.id)
        bmi = self.bmi_calculator.get_bmi(username)
        if bmi == -1:
            return Response('No weight value on recorded!\nUse !log weight # to record your most recent weight.', reply=True, delete_after=0)
        elif bmi == 0:
            return Response("No height value on record!\nUser !height 1'2 to record your most recent height")
        await self.send_file(channel,'images\BMI_Chart.jpg')
        return Response('Your bmi score is:\n'+ str(bmi)+"\nweight: "+str(self.bmi_calculator.get_weight(username))+"\nheight: "+str(self.bmi_calculator.get_height(username)), reply=True, delete_after=0)

    async def _cmd_signup(self, author, message):
        username =  author.name +"#"+author.discriminator
        if username in self.database.data_list["users"].keys():
            return Response('You have already registered! `%s`' % author.name, reply=True, delete_after=0)
        else:
            self.database.add_user(username,author.id)
            return Response('Registration complete! `%s`' % author.name, reply=True, delete_after=0)

    async def _cmd_delete_account(self, author, message):
        username =  author.name +"#"+author.discriminator
        if username not in self.database.data_list["users"].keys():
            return Response('You are not registered yet! `%s`' % author.name, reply=True, delete_after=0)
        else:
            self.database.remove_user(username)
            return Response('Sucessfully deleted account! `%s`' % author.name, reply=True, delete_after=0)

    
    async def reminder_loop(self):
        await self.wait_until_ready()
        while not self.is_closed:
            await self.update_stat_message()
            for user in self.database.data_list["users"]:#user is string
                for reminder in self.database.data_list["users"][user]["reminders"]:#reminder is dictionary in reminders array
                    date_now = str(datetime.now(timezone('US/Pacific')).month)+"/"+str(datetime.now(timezone('US/Pacific')).day)+"/"+str(datetime.now(timezone('US/Pacific')).year)
                    time_now = str(datetime.now(timezone('US/Pacific')).hour)+":"+str(datetime.now(timezone('US/Pacific')).minute)
                    if time_now == reminder["reminder_time"]: #if current time and current date
                        if date_now == reminder["reminder_date"]:
                            user_object = discord.User()
                            user_object.name = self.database.data_list["users"][user]["discord_username"] #Username with #0000
                            user_object.id = self.database.data_list["users"][user]["discord_id"] #ID Number
                            await self.safe_send_message(user_object, reminder["reminder_name"])#Direct Message Reminder Name
                            self.database.data_list["users"][user]["reminders"].remove(reminder)
                            self.database.write_json_database()
                            self.database.write_bkup_database()
            await asyncio.sleep(60) #check every 60 secs

    async def _cmd_remove_category(self, author, message,channel):
        username =  author.name +"#"+author.discriminator
        confirm_msg = await self.safe_send_message(channel, "Reply with emoji workout")
        response_msg = await self.wait_for_message(30, author=author, channel=channel)
        if not response_msg:
            await self.safe_delete_message(confirm_msg)
            return Response("Ok nevermind.", delete_after=30)
        if "emoji_workouts" in self.database.data_list["users"][username]:
            del self.database.data_list["users"][username]["emoji_workouts"][response_msg.content[0]]
        else:
            return Response('No custom workouts logged!', reply=True, delete_after=0)       
        self.database.write_json_database()
        self.database.write_bkup_database()
        await self.safe_send_message(channel, "Success!")
        
    async def _cmd_add_category(self, author, message,channel):
        username =  author.name +"#"+author.discriminator
        confirm_msg = await self.safe_send_message(channel, "Reply with category name")
        response_msg = await self.wait_for_message(30, author=author, channel=channel)
        if not response_msg:
            await self.safe_delete_message(confirm_msg)
            return Response("Ok nevermind.", delete_after=30)
        confirm_emoji =await self.safe_send_message(channel, "Reply with emoji")
        response_emoji = await self.wait_for_message(30, author=author, channel=channel)
        if not response_emoji:
            await self.safe_delete_message( confirm_emoji)
            return Response("Ok nevermind.", delete_after=30)
        
        if "emoji_workouts" in self.database.data_list["users"][username]:
            self.database.data_list["users"][username]["emoji_workouts"][response_emoji.content[0]]=response_msg.content.split(" ")[0].lower()
        else:
            self.database.data_list["users"][username]["emoji_workouts"] = {}
            self.database.data_list["users"][username]["emoji_workouts"][response_emoji.content[0]]=response_msg.content.split(" ")[0].lower()
        
        self.database.write_json_database()
        self.database.write_bkup_database()
        await self.safe_send_message(channel, "Success!")
        
    async def cmd_emoji(self, author, message,channel):
        await self.update_stat_message()
        username =  author.name +"#"+author.discriminator
        if username not in self.database.data_list["users"].keys():
            self.database.add_user(username,author.id)
        botmsg = await self.send_message(message.channel,"Log Workout with Reaction:\nCategory:\nValue: ")
        self.database.data_list["users"][username]["emoji_log"] = botmsg.id;
        self.database.write_json_database()
        self.database.write_bkup_database()
        await self.add_reaction(botmsg,"🔢")
        #await self.add_reaction(botmsg,"⬅")
        await self.add_reaction(botmsg,"💪")
        await self.add_reaction(botmsg,"🗂")
        await self.add_reaction(botmsg,"☑")
        await self.add_reaction(botmsg,"🔄")
        
    async def cmd_reminders(self, author, message,channel):
        await self.update_stat_message()
        username =  author.name +"#"+author.discriminator
        if username not in self.database.data_list["users"].keys():
            self.database.add_user(username,author.id)
        if "routine_list" not in self.database.data_list["users"][username]:
            self.exercises.create_default_routines(username)
        Menu_UI ="Reminder List for user "+username+":\n"+self.database.user_reminders(username)
        
        botmsg = await self.send_message(message.channel,Menu_UI)
        self.database.data_list["users"][username]["reminder_log"] = botmsg.id;
        self.database.write_json_database()
        self.database.write_bkup_database()
        await self.add_reaction(botmsg,"➕")#plus
        await self.add_reaction(botmsg,"➖")#minus
        await self.add_reaction(botmsg,"🔄")

    async def cmd_routine(self, author, message,channel):
        await self.update_stat_message()
        username =  author.name +"#"+author.discriminator
        if username not in self.database.data_list["users"].keys():
            self.database.add_user(username,author.id)
        if "routine_list" not in self.database.data_list["users"][username]:
            self.exercises.create_default_routines(username)
        Menu_UI ="```Routine Menu```"+self.exercises.routine_menu_string(username)
        
        botmsg = await self.send_message(message.channel,Menu_UI)
        self.database.data_list["users"][username]["routine_emoji_log"] = botmsg.id;
        self.database.write_json_database()
        self.database.write_bkup_database()
        await self.add_reaction(botmsg,"🔢")
        await self.add_reaction(botmsg,"➕")#plus
        await self.add_reaction(botmsg,"➖")#minus
        await self.add_reaction(botmsg,"🔄")

    async def _cmd_exercise_menu(self, author, message,channel,r):
        username =  author.name +"#"+author.discriminator
        if username not in self.database.data_list["users"].keys():
            self.database.add_user(username,author.id)
        if "routine_list" not in self.database.data_list["users"][username]:
            self.exercises.create_default_routines(username)
        Menu_UI = "```Exercise Menu```"+self.exercises.exercise_menu_string(username, r)
        
        botmsg = await self.send_message(message.channel,Menu_UI)
        self.database.data_list["users"][username]["exercise_emoji_log"] = botmsg.id;
        self.database.write_json_database()
        self.database.write_bkup_database()
        await self.add_reaction(botmsg,"🔢")
        await self.add_reaction(botmsg,"➕")#plus
        await self.add_reaction(botmsg,"➖")#minus
        await self.add_reaction(botmsg,"⬅")#back
        await self.add_reaction(botmsg,"🔄")
        
    async def _cmd_set_menu(self, author, message,channel,r,e):
        username =  author.name +"#"+author.discriminator
        if username not in self.database.data_list["users"].keys():
            self.database.add_user(username,author.id)
        if "routine_list" not in self.database.data_list["users"][username]:
            self.exercises.create_default_routines(username)
        Menu_UI = "```Set Menu```"+self.exercises.set_menu_string(username, r,e)
        
        botmsg = await self.send_message(message.channel,Menu_UI)
        self.database.data_list["users"][username]["set_emoji_log"] = botmsg.id;
        self.database.write_json_database()
        self.database.write_bkup_database()
        await self.add_reaction(botmsg,"➕")#plus
        await self.add_reaction(botmsg,"➖")#minus
        await self.add_reaction(botmsg,"⬅")#back
        await self.add_reaction(botmsg,"🔄")

    async def on_reaction_add(self,reaction,user):
        username =user.name +"#"+user.discriminator
        msg = reaction.message
        chat = msg.channel
        
        if username in self.database.data_list["users"]:
            if "reminder_log" in self.database.data_list["users"][username]:
                if reaction.emoji == "➕" and str(msg.id) == self.database.data_list["users"][username]["reminder_log"]:
                    confirm_name_msg = await self.safe_send_message(msg.channel, "Reply with reminder text to log")
                    response_name_msg = await self.wait_for_message(30, author=user, channel=msg.channel)
                    if not response_name_msg:
                        await self.safe_delete_message(confirm_name_msg)
                        await self.send_message(msg.channel,'Ok Nevermind...')
                        return
                        
                    confirm_month_msg = await self.safe_send_message(msg.channel, "Reply with **month** date for reminder")
                    response_month_msg = await self.wait_for_message(30, author=user, channel=msg.channel)
                    if not response_month_msg:
                        await self.safe_delete_message(confirm_month_msg)
                        await self.send_message(msg.channel,'Ok Nevermind...')
                        return
                    try:
                        month_value = int(response_month_msg.content)
                        if month_value>12 or month_value<=0:
                            await self.send_message(msg.channel,'Invalid Month Range Response')
                            return
                        
                        confirm_day_msg = await self.safe_send_message(msg.channel, "Reply with **day** date for reminder")
                        response_day_msg = await self.wait_for_message(30, author=user, channel=msg.channel)
                        if not response_day_msg:
                            await self.safe_delete_message(confirm_day_msg)
                            await self.send_message(msg.channel,'Ok Nevermind...')
                            return
                        try:
                            day_value = int(response_day_msg.content)
                            if day_value>31 or day_value<=0:
                                await self.send_message(msg.channel,'Invalid Day Response')
                                return
                            
                            confirm_ampm_msg = await self.safe_send_message(msg.channel, "Reply with text **am** or **pm** time for reminder")
                            response_ampm_msg = await self.wait_for_message(30, author=user, channel=msg.channel)
                            if not response_ampm_msg:
                                await self.safe_delete_message(confirm_ampm_msg)
                                await self.send_message(msg.channel,'Ok Nevermind...')
                                return
                            try:
                                ampm_value = "am"
                                if response_ampm_msg.content.lower().strip() == "am":
                                    ampm_value = "am"
                                elif response_ampm_msg.content.lower().strip() == "pm":
                                    ampm_value = "pm"
                                else:
                                    await self.send_message(msg.channel,'Invalid am/pm Response')
                                    return
                                confirm_hour_msg = await self.safe_send_message(msg.channel, "Reply with **hour** number for reminder")
                                response_hour_msg = await self.wait_for_message(30, author=user, channel=msg.channel)
                                if not response_hour_msg:
                                    await self.safe_delete_message(confirm_hour_msg)
                                    await self.send_message(msg.channel,'Ok Nevermind...')
                                    return
                                try:
                                    hour_value = int(response_hour_msg.content)
                                    if hour_value<0 or hour_value>12:
                                        await self.send_message(msg.channel,'Invalid Hour Response')
                                        return
                                    confirm_minute_msg = await self.safe_send_message(msg.channel, "Reply with **minute** number for reminder")
                                    response_minute_msg = await self.wait_for_message(30, author=user, channel=msg.channel)
                                    if not response_minute_msg:
                                        await self.safe_delete_message(confirm_minute_msg)
                                        await self.send_message(msg.channel,'Ok Nevermind...')
                                        return
                                    try:
                                        minute_value = int(response_minute_msg.content)
                                        if minute_value<0 or minute_value>60:
                                            await self.send_message(msg.channel,'Invalid Minute Response')
                                            return
                                        try:
                                            year_value = int(datetime.now(timezone('US/Pacific')).year)
                                            if month_value < int(datetime.now(timezone('US/Pacific')).month):
                                                year_value +=1
                                            elif month_value == int(datetime.now(timezone('US/Pacific')).month):
                                                if day_value < int(datetime.now(timezone('US/Pacific')).day):
                                                    year_value +=1
                                            if ampm_value == "pm":
                                                if hour_value!=12:
                                                    hour_value+=12
                                                if hour_value==0:
                                                    hour_value+=12
                                            if ampm_value == "am":
                                                if hour_value==12:
                                                    hour_value-=12
                                            self.database.add_reminder(username,str(month_value)+"/"+str(day_value)+"/"+str(year_value),str(hour_value),str(minute_value),response_name_msg.content)
                                            self.database.write_json_database()
                                            self.database.write_bkup_database()
                                            await self.safe_delete_message(msg)
                                            await self.cmd_reminders(user,msg,chat)
                                        except:
                                            await self.send_message(msg.channel,'Invalid Reminder Response')
                                    except:
                                        await self.send_message(msg.channel,'Invalid Minute Response') 
                                except:
                                    await self.send_message(msg.channel,'Invalid Hour Response')
                            except:
                                await self.send_message(msg.channel,'Invalid am/pm Response')
                        except:
                            await self.send_message(msg.channel,'Invalid Day Response')
                    except:
                        await self.send_message(msg.channel,'Invalid Month Response')
                    
                    try:
                        await self.remove_reaction(msg,reaction.emoji,user)
                    except:
                        print("Can't auto remove emoji")
                elif reaction.emoji == "➖" and str(msg.id) == self.database.data_list["users"][username]["reminder_log"]:
                    confirm_msg = await self.safe_send_message(msg.channel, "Reply with reminder number to remove")
                    response_msg = await self.wait_for_message(30, author=user, channel=msg.channel)
                    if not response_msg:
                        await self.safe_delete_message(confirm_msg)
                        await self.send_message(msg.channel,'Ok Nevermind...')
                        return
                    try:
                        value = int(response_msg.content)
                        del self.database.data_list["users"][username]["reminders"][value-1]
                        self.database.write_json_database()
                        self.database.write_bkup_database()
                        await self.safe_delete_message(msg)
                        await self.safe_delete_message(confirm_msg)
                        await self.safe_delete_message(response_msg)
                        await self.cmd_reminders(user,msg,chat)
                    except:
                        await self.safe_delete_message(confirm_msg)
                        await self.send_message(msg.channel,'Invalid Response')
                    finally:
                        try:
                            await self.remove_reaction(msg,reaction.emoji,user)
                        except:
                            print("Can't auto remove emoji")
                elif reaction.emoji == "🔄" and str(msg.id) == self.database.data_list["users"][username]["reminder_log"]:
                        await self.cmd_reminders(user,msg,chat)
                        await self.safe_delete_message(msg)
            if "routine_emoji_log" in self.database.data_list["users"][username]:
                if reaction.emoji == "🔢" and str(msg.id) == self.database.data_list["users"][username]["routine_emoji_log"]:
                    confirm_msg = await self.safe_send_message(msg.channel, "Reply with routine number to select")
                    response_msg = await self.wait_for_message(30, author=user, channel=msg.channel)
                    if not response_msg:
                        await self.safe_delete_message(confirm_msg)
                        await self.send_message(msg.channel,'Ok Nevermind...')
                        return
                    try:
                        value = int(response_msg.content)
                        await self._cmd_exercise_menu(user, msg,chat,self.database.data_list["users"][username]["routine_list"][value-1]["name"])
                        self.database.data_list["users"][username]["last_routine"] = self.database.data_list["users"][username]["routine_list"][value-1]["name"]
                        await self.safe_delete_message(msg)
                        await self.safe_delete_message(confirm_msg)
                        await self.safe_delete_message(response_msg)
                    except:
                        await self.safe_delete_message(confirm_msg)
                        await self.send_message(msg.channel,'Invalid Response')
                    finally:
                        try:
                            await self.remove_reaction(msg,reaction.emoji,user)
                        except:
                            print("Can't auto remove emoji")
                elif reaction.emoji == "➕" and str(msg.id) == self.database.data_list["users"][username]["routine_emoji_log"]:
                    confirm_msg = await self.safe_send_message(msg.channel, "Reply with routine name to add")
                    response_msg = await self.wait_for_message(30, author=user, channel=msg.channel)
                    if not response_msg:
                        await self.safe_delete_message(confirm_msg)
                        await self.send_message(msg.channel,'Ok Nevermind...')
                        return
                    try:
                        self.exercises.add_routine(username, response_msg.content)
                        await self.safe_delete_message(msg)
                        await self.safe_delete_message(confirm_msg)
                        await self.safe_delete_message(response_msg)
                        await self.cmd_routine(user,msg,chat)
                    except:
                        await self.safe_delete_message(confirm_msg)
                        await self.send_message(msg.channel,'Invalid Response')
                    finally:
                        try:
                            await self.remove_reaction(msg,reaction.emoji,user)
                        except:
                            print("Can't auto remove emoji")
                elif reaction.emoji == "➖" and str(msg.id) == self.database.data_list["users"][username]["routine_emoji_log"]:
                    confirm_msg = await self.safe_send_message(msg.channel, "Reply with routine number to remove")
                    response_msg = await self.wait_for_message(30, author=user, channel=msg.channel)
                    if not response_msg:
                        await self.safe_delete_message(confirm_msg)
                        await self.send_message(msg.channel,'Ok Nevermind...')
                        return
                    try:
                        value = int(response_msg.content)
                        del self.database.data_list["users"][username]["routine_list"][value-1]
                        self.database.write_json_database()
                        self.database.write_bkup_database()
                        await self.safe_delete_message(msg)
                        await self.safe_delete_message(confirm_msg)
                        await self.safe_delete_message(response_msg)
                        await self.cmd_routine(user,msg,chat)
                    except:
                        await self.safe_delete_message(confirm_msg)
                        await self.send_message(msg.channel,'Invalid Response')
                    finally:
                        try:
                            await self.remove_reaction(msg,reaction.emoji,user)
                        except:
                            print("Can't auto remove emoji")
                elif reaction.emoji == "🔄" and str(msg.id) == self.database.data_list["users"][username]["routine_emoji_log"]:
                        await self.cmd_routine(user,msg,chat)
                        await self.safe_delete_message(msg)
            if "exercise_emoji_log" in self.database.data_list["users"][username]:
                if reaction.emoji == "🔢" and str(msg.id) == self.database.data_list["users"][username]["exercise_emoji_log"]:
                    confirm_msg = await self.safe_send_message(msg.channel, "Reply with exercise number to select")
                    response_msg = await self.wait_for_message(30, author=user, channel=msg.channel)
                    if not response_msg:
                        await self.safe_delete_message(confirm_msg)
                        await self.send_message(msg.channel,'Ok Nevermind...')
                        return
                    try:
                        value = int(response_msg.content)
                        await self._cmd_set_menu(user, msg,chat,self.database.data_list["users"][username]["last_routine"],self.exercises.get_exercise_name_by_int(username,self.database.data_list["users"][username]["last_routine"], value-1))
                        self.database.data_list["users"][username]["last_exercise"] = self.exercises.get_exercise_name_by_int(username,self.database.data_list["users"][username]["last_routine"], value-1)
                        await self.safe_delete_message(msg)
                        await self.safe_delete_message(confirm_msg)
                        await self.safe_delete_message(response_msg)
                    except:
                        await self.safe_delete_message(confirm_msg)
                        await self.send_message(msg.channel,'Invalid Response')
                    finally:
                        try:
                            await self.remove_reaction(msg,reaction.emoji,user)
                        except:
                            print("Can't auto remove emoji")
                elif reaction.emoji == "➕" and str(msg.id) == self.database.data_list["users"][username]["exercise_emoji_log"]:
                    confirm_msg = await self.safe_send_message(msg.channel, "Reply with exercise name to add")
                    response_msg = await self.wait_for_message(30, author=user, channel=msg.channel)
                    if not response_msg:
                        await self.safe_delete_message(confirm_msg)
                        await self.send_message(msg.channel,'Ok Nevermind...')
                        return
                    try:
                        self.exercises.add_excercise_to_routine(username, self.database.data_list["users"][username]["last_routine"], response_msg.content)
                        await self.safe_delete_message(msg)
                        await self.safe_delete_message(confirm_msg)
                        await self.safe_delete_message(response_msg)
                        await self._cmd_exercise_menu(user, msg,chat,self.database.data_list["users"][username]["last_routine"])
                    except:
                        await self.safe_delete_message(confirm_msg)
                        await self.send_message(msg.channel,'Invalid Response')
                    finally:
                        try:
                            await self.remove_reaction(msg,reaction.emoji,user)
                        except:
                            print("Can't auto remove emoji")
                elif reaction.emoji == "➖" and str(msg.id) == self.database.data_list["users"][username]["exercise_emoji_log"]:
                    confirm_msg = await self.safe_send_message(msg.channel, "Reply with exercise number to remove")
                    response_msg = await self.wait_for_message(30, author=user, channel=msg.channel)
                    if not response_msg:
                        await self.safe_delete_message(confirm_msg)
                        await self.send_message(msg.channel,'Ok Nevermind...')
                        return
                    try:
                        value = int(response_msg.content)
                        for r in self.database.data_list["users"][username]["routine_list"]:
                            if r["name"]==self.database.data_list["users"][username]["last_routine"]:
                                del r["exercises"][value-1]
                        self.database.write_json_database()
                        self.database.write_bkup_database()
                        await self.safe_delete_message(msg)
                        await self.safe_delete_message(confirm_msg)
                        await self.safe_delete_message(response_msg)
                        await self._cmd_exercise_menu(user, msg,chat,self.database.data_list["users"][username]["last_routine"])
                    except:
                        await self.safe_delete_message(confirm_msg)
                        await self.send_message(msg.channel,'Invalid Response')
                    finally:
                        try:
                            await self.remove_reaction(msg,reaction.emoji,user)
                        except:
                            print("Can't auto remove emoji")
                elif reaction.emoji == "⬅" and str(msg.id) == self.database.data_list["users"][username]["exercise_emoji_log"]:
                    await self.cmd_routine(user, msg,chat)
                    await self.safe_delete_message(msg)
                elif reaction.emoji == "🔄" and str(msg.id) == self.database.data_list["users"][username]["exercise_emoji_log"]:
                        await self._cmd_exercise_menu(user, msg,chat,self.database.data_list["users"][username]["last_routine"])
                        await self.safe_delete_message(msg)   
            if "set_emoji_log" in self.database.data_list["users"][username]:
                if reaction.emoji == "➕" and str(msg.id) == self.database.data_list["users"][username]["set_emoji_log"]:
                    confirm_rep_msg = await self.safe_send_message(msg.channel, "Reply with number of reps done")
                    response_rep_msg = await self.wait_for_message(30, author=user, channel=msg.channel)
                    if not response_rep_msg:
                        await self.safe_delete_message(confirm_rep_msg)
                        await self.send_message(msg.channel,'Ok Nevermind...')
                        return
                    try:
                        rep_value = int(response_rep_msg.content)
                    except:
                        await self.safe_delete_message(confirm_rep_msg)
                        await self.send_message(msg.channel,'Invalid Rep Number Response')
                        return
                    confirm_weight_msg = await self.safe_send_message(msg.channel, "Reply with rep weight number")
                    response_weight_msg = await self.wait_for_message(30, author=user, channel=msg.channel)
                    if not response_weight_msg:
                        await self.safe_delete_message(confirm_weight_msg)
                        await self.send_message(msg.channel,'Ok Nevermind...')
                        return
                    try:
                        weight_value = int(response_weight_msg.content)
                    except:
                        await self.safe_delete_message(confirm_weight_msg)
                        await self.send_message(msg.channel,'Invalid Weight Number Response')
                        return
                    try:
                        self.exercises.set_excercise_reps_weight_today(username, self.database.data_list["users"][username]["last_routine"],self.database.data_list["users"][username]["last_exercise"],rep_value,weight_value)
                        await self.safe_delete_message(msg)
                        await self._cmd_set_menu(user, msg,chat,self.database.data_list["users"][username]["last_routine"],self.database.data_list["users"][username]["last_exercise"])
                    except:
                        await self.send_message(msg.channel,'Invalid Response')
                    finally:
                        try:
                            await self.remove_reaction(msg,reaction.emoji,user)
                        except:
                            print("Can't auto remove emoji")
                elif reaction.emoji == "➖" and str(msg.id) == self.database.data_list["users"][username]["set_emoji_log"]:
                    confirm_msg = await self.safe_send_message(msg.channel, "Reply with set number to remove")
                    response_msg = await self.wait_for_message(30, author=user, channel=msg.channel)
                    if not response_msg:
                        await self.safe_delete_message(confirm_msg)
                        await self.send_message(msg.channel,'Ok Nevermind...')
                        return
                    try:
                        value = int(response_msg.content)
                        check_date = datetime.now(timezone('US/Pacific'))
                        check_string = str(check_date.month)+"/"+str(check_date.day)+"/"+str(check_date.year)
                        latest_log = self.plotter.get_log_by_date(username,check_string)
                        for r in latest_log["routines"]:
                            if r["name"]==self.database.data_list["users"][username]["last_routine"]:
                                for e in r["exercises"]:
                                    if e["exercise_name"]==self.database.data_list["users"][username]["last_exercise"]:
                                        del e["sets"][value-1]
                        self.database.write_json_database()
                        self.database.write_bkup_database()
                        await self.safe_delete_message(msg)
                        await self.safe_delete_message(confirm_msg)
                        await self.safe_delete_message(response_msg)
                        await self._cmd_set_menu(user, msg,chat,self.database.data_list["users"][username]["last_routine"],self.database.data_list["users"][username]["last_exercise"])
                    except:
                        await self.safe_delete_message(confirm_msg)
                        await self.send_message(msg.channel,'Invalid Response')
                    finally:
                        try:
                            await self.remove_reaction(msg,reaction.emoji,user)
                        except:
                            print("Can't auto remove emoji")
                elif reaction.emoji == "⬅" and str(msg.id) == self.database.data_list["users"][username]["set_emoji_log"]:
                    await self._cmd_exercise_menu(user, msg,chat,self.database.data_list["users"][username]["last_routine"])
                    await self.safe_delete_message(msg)
                elif reaction.emoji == "🔄" and str(msg.id) == self.database.data_list["users"][username]["set_emoji_log"]:
                        await self._cmd_set_menu(user, msg,chat,self.database.data_list["users"][username]["last_routine"],self.database.data_list["users"][username]["last_exercise"])
                        await self.safe_delete_message(msg)   
            if "emoji_log" in self.database.data_list["users"][username]:
                bot_object = discord.User()
                bot_object.name = "Fitness#7651"
                bot_object.id = "368455430814564372"
                try:
                    temp_str = reaction.emoji.name
                    for i in self.get_all_emojis():
                        if reaction.emoji.name == "period":
                            if "." not in msg.content.split(":")[-1]:
                                await self.edit_message(msg,msg.content+".")
                            try:
                                await self.remove_reaction(msg,reaction.emoji,user)
                            except:
                                print("Can't auto remove emoji")
                            break
                        elif reaction.emoji.name == i.name:
                            edit_string = msg.content.split("\n")
                            new_string = edit_string[0]+"\n"+edit_string[1].split(":")[0]+": "+reaction.emoji.name+"\n"+edit_string[2]
                            await self.edit_message(msg,new_string)
                            try:
                                await self.remove_reaction(msg,reaction.emoji,user)
                            except:
                                print("Can't auto remove emoji")
                except:
                    temp_str = reaction.emoji
                finally:
                    if "emoji_workouts" in self.database.data_list["users"][username]:
                        for i in self.database.data_list["users"][username]["emoji_workouts"]:
                            if reaction.emoji == str(i) and str(msg.id) == self.database.data_list["users"][username]["emoji_log"]:
                                edit_string = msg.content.split("\n")
                                new_string = edit_string[0]+"\n"+edit_string[1].split(":")[0]+": "+self.database.data_list["users"][username]["emoji_workouts"][i]+"\n"+edit_string[2]
                                await self.edit_message(msg,new_string)
                                try:
                                    await self.remove_reaction(msg,reaction.emoji,user)
                                except:
                                    print("Can't auto remove emoji")
                    if reaction.emoji == "💪" and str(msg.id) == self.database.data_list["users"][username]["emoji_log"]:
                        await self.add_reaction(msg,"⚖")
                        await self.add_reaction(msg,"📏")
                        await self.add_reaction(msg,"🛌")
                        await self.add_reaction(msg,"🍽")
                        await self.add_reaction(msg,"🔥")
                        await self.add_reaction(msg,"🏃")
                        await self.add_reaction(msg,"👟")
                        for i in self.get_all_emojis():
                            if i.name != "period":
                                await self.add_reaction(msg,i)
                        if "emoji_workouts" in self.database.data_list["users"][username]:
                            for i in self.database.data_list["users"][username]["emoji_workouts"]:
                                await self.add_reaction(msg,i)
                    elif reaction.emoji == "🔢" and str(msg.id) == self.database.data_list["users"][username]["emoji_log"]:
                        confirm_msg = await self.safe_send_message(msg.channel, "Reply with number value")
                        response_msg = await self.wait_for_message(30, author=user, channel=msg.channel)
                        if not response_msg:
                            await self.safe_delete_message(confirm_msg)
                            await self.send_message(msg.channel,'Ok Nevermind...')
                        try:
                            value = float(response_msg.content)
                            edit_string = msg.content.split("\n")
                            new_string = edit_string[0]+"\n"+edit_string[1]+"\n"+edit_string[2].split(":")[0]+": "+str(value)
                            await self.edit_message(msg,new_string)
                            await self.safe_delete_message(confirm_msg)
                            await self.safe_delete_message(response_msg)
                        except:
                            await self.safe_delete_message(confirm_msg)
                            await self.send_message(msg.channel,'Invalid Response')
                        finally:
                            try:
                                await self.remove_reaction(msg,reaction.emoji,user)
                            except:
                                print("Can't auto remove emoji")
                    elif reaction.emoji == "🗂" and str(msg.id) == self.database.data_list["users"][username]["emoji_log"]:
                        await self.add_reaction(msg,"📋")
                        await self.add_reaction(msg,"📈")
                        await self.add_reaction(msg,"📊")
                    elif reaction.emoji == "📋" and str(msg.id) == self.database.data_list["users"][username]["emoji_log"]:
                        check_date = datetime.now(timezone('US/Pacific'))
                        check_string = str(check_date.month)+"/"+str(check_date.day)+"/"+str(check_date.year)
                        latest_log = self.plotter.get_log_by_date(username,check_string)
                        if not latest_log:
                            await self.send_message(msg.channel,'```No log inputted for today!```')
                        else:
                            await self.send_message(msg.channel,'```Latest Log:\n'+str(json.dumps(latest_log))+'```')
                        try:
                            await self.remove_reaction(msg,reaction.emoji,user)
                        except:
                            print("Can't auto remove emoji")       
                    elif reaction.emoji == "📈" and str(msg.id) == self.database.data_list["users"][username]["emoji_log"]:
                        edit_string = msg.content.split("\n")
                        category = edit_string[1].split(":")[1].strip()
                        try:
                            value = int(float(edit_string[2].split(":")[1].strip()))
                        except:
                            value = 10
                        latest = value
                        if latest<10:
                            latest = 10
                        if self.plotter.generate_chart(username, category,latest) == "Empty List":
                            await self.send_message(msg.channel,'```No data to Chart for Category: "'+category+'"```')
                        else:
                            await self.send_file(msg.channel,"plot_graphs/"+username+"_"+category+"_graph.png")
                        try:
                            await self.remove_reaction(msg,reaction.emoji,user)
                        except:
                            print("Can't auto remove emoji")
                    elif reaction.emoji == "📊" and str(msg.id) == self.database.data_list["users"][username]["emoji_log"]:
                        bmi = self.bmi_calculator.get_bmi(username)
                        if bmi == -1:
                            await self.send_message(msg.channel,'No weight value on record!\nUse ⚖ emoji to record your most recent weight.')
                        elif bmi == 0:
                            await self.send_message(msg.channel,'No height value on record!\nUse 📏 emoji to record your most recent height\nUse "." as a seperator {ft}.{in}')
                        else:
                            await self.send_file(msg.channel,'images\BMI_Chart.jpg')
                            await self.send_message(msg.channel,'Your bmi score is:\n'+ str(bmi)+"\nweight: "+str(self.bmi_calculator.get_weight(username))+"\nheight: "+str(self.bmi_calculator.get_height(username)))
                        try:
                            await self.remove_reaction(msg,reaction.emoji,user)
                        except:
                            print("Can't auto remove emoji")
                    elif reaction.emoji == "🔄" and str(msg.id) == self.database.data_list["users"][username]["emoji_log"]:
                        await self.cmd_emoji(user, msg,chat)
                        try:
                            await self.remove_reaction(msg,reaction.emoji,user)
                        except:
                            print("Can't auto remove emoji")
                    elif reaction.emoji == "🏃" and str(msg.id) == self.database.data_list["users"][username]["emoji_log"]:
                        edit_string = msg.content.split("\n")
                        new_string = edit_string[0]+"\n"+edit_string[1].split(":")[0]+": "+"miles\n"+edit_string[2]
                        await self.edit_message(msg,new_string)
                        try:
                            await self.remove_reaction(msg,reaction.emoji,user)
                        except:
                            print("Can't auto remove emoji")
                    elif reaction.emoji == "👟" and str(msg.id) == self.database.data_list["users"][username]["emoji_log"]:
                        edit_string = msg.content.split("\n")
                        new_string = edit_string[0]+"\n"+edit_string[1].split(":")[0]+": "+"steps\n"+edit_string[2]
                        await self.edit_message(msg,new_string)
                        try:
                            await self.remove_reaction(msg,reaction.emoji,user)
                        except:
                            print("Can't auto remove emoji")
                    elif reaction.emoji == "⚖" and str(msg.id) == self.database.data_list["users"][username]["emoji_log"]:
                        edit_string = msg.content.split("\n")
                        new_string = edit_string[0]+"\n"+edit_string[1].split(":")[0]+": "+"weight\n"+edit_string[2]
                        await self.edit_message(msg,new_string)
                        try:
                            await self.remove_reaction(msg,reaction.emoji,user)
                        except:
                            print("Can't auto remove emoji")
                    elif reaction.emoji == "📏" and str(msg.id) == self.database.data_list["users"][username]["emoji_log"]:
                        edit_string = msg.content.split("\n")
                        new_string = edit_string[0]+"\n"+edit_string[1].split(":")[0]+": "+"height\n"+edit_string[2]
                        await self.edit_message(msg,new_string)
                        try:
                            await self.remove_reaction(msg,reaction.emoji,user)
                        except:
                            print("Can't auto remove emoji")
                    elif reaction.emoji == "🛌" and str(msg.id) == self.database.data_list["users"][username]["emoji_log"]:
                        edit_string = msg.content.split("\n")
                        new_string = edit_string[0]+"\n"+edit_string[1].split(":")[0]+": "+"sleep\n"+edit_string[2]
                        await self.edit_message(msg,new_string)
                        try:
                            await self.remove_reaction(msg,reaction.emoji,user)
                        except:
                            print("Can't auto remove emoji")
                    elif reaction.emoji == "🍽" and str(msg.id) == self.database.data_list["users"][username]["emoji_log"]:
                        edit_string = msg.content.split("\n")
                        new_string = edit_string[0]+"\n"+edit_string[1].split(":")[0]+": "+"calorie_intake\n"+edit_string[2]
                        await self.edit_message(msg,new_string)
                        try:
                            await self.remove_reaction(msg,reaction.emoji,user)
                        except:
                            print("Can't auto remove emoji")
                    elif reaction.emoji == "🔥" and str(msg.id) == self.database.data_list["users"][username]["emoji_log"]:
                        edit_string = msg.content.split("\n")
                        new_string = edit_string[0]+"\n"+edit_string[1].split(":")[0]+": "+"calorie_burn\n"+edit_string[2]
                        await self.edit_message(msg,new_string)
                        try:
                            await self.remove_reaction(msg,reaction.emoji,user)
                        except:
                            print("Can't auto remove emoji")
                    elif reaction.emoji == "☑" and str(msg.id) == self.database.data_list["users"][username]["emoji_log"]:
                        try:
                            edit_string = msg.content.split("\n")
                            category = edit_string[1].split(":")[1].strip()
                            if category == "height":
                                value = edit_string[2].split(":")[1].strip().split(".")[0]+"'"+edit_string[2].split(":")[1].strip().split(".")[1]
                                self.bmi_calculator.set_height(username, value)
                                await self.send_message(msg.channel,'Sucessfully modified user height!\n    Height: '+value)
                            else:
                                value = float(edit_string[2].split(":")[1].strip())
                                self.plotter.set_category_today(username,category,value)
                                date_now = str(datetime.now(timezone('US/Pacific')).month)+"/"+str(datetime.now(timezone('US/Pacific')).day)+"/"+str(datetime.now(timezone('US/Pacific')).year)
                                if category == "weight":
                                    self.bmi_calculator.set_weight(username,value)
                                await self.send_message(msg.channel,'Sucessfully modified todays log!\n    Date: '+date_now+'\n    Category: '+category+"\n    value: "+str(value))
                        except:
                            await self.send_message(msg.channel,'Could not modify log! Check format')
                        try:
                            await self.remove_reaction(msg,reaction.emoji,user)
                        except:
                            print("Can't auto remove emoji")
                        
    async def on_reaction_remove(self,reaction,user):
        username =user.name +"#"+user.discriminator
        msg = reaction.message
        chat = msg.channel
        
        if username in self.database.data_list["users"]:
            if "emoji_log" in self.database.data_list["users"][username]:
                try:
                    temp_str = reaction.emoji.name
                except:
                    temp_str = reaction.emoji
                finally:
                    bot_object = discord.User()
                    bot_object.name = "Fitness#7651"
                    bot_object.id = "368455430814564372"
                    if reaction.emoji == "💪" and str(msg.id) == self.database.data_list["users"][username]["emoji_log"]:
                        await self.remove_reaction(msg,"⚖",bot_object)
                        await self.remove_reaction(msg,"📏",bot_object)
                        await self.remove_reaction(msg,"🛌",bot_object)
                        await self.remove_reaction(msg,"🍽",bot_object)
                        await self.remove_reaction(msg,"🔥",bot_object)
                        await self.remove_reaction(msg,"🏃",bot_object)
                        await self.remove_reaction(msg,"👟",bot_object)
                        for i in self.get_all_emojis():
                            if i.name != "period":
                                await self.remove_reaction(msg,i,bot_object)
                        if "emoji_workouts" in self.database.data_list["users"][username]:
                            for i in self.database.data_list["users"][username]["emoji_workouts"]:
                                await self.remove_reaction(msg,str(i),bot_object)
                    elif reaction.emoji == "🗂" and str(msg.id) == self.database.data_list["users"][username]["emoji_log"]:
                        await self.remove_reaction(msg,"📋",bot_object)
                        await self.remove_reaction(msg,"📈",bot_object)
                        await self.remove_reaction(msg,"📊",bot_object)
####################################################################################
    async def on_message(self, message):
        await self.wait_until_ready()

        message_content = message.content.strip()
        print("[Chat]: "+message_content)
 
        if not message_content.startswith(self.config.command_prefix):
            return

        if message.author == self.user:
            self.safe_print("Ignoring command from myself (%s)" % message.content)
            return

        if self.config.bound_channels and message.channel.id not in self.config.bound_channels and not message.channel.is_private:
            return  # if I want to log this I just move it under the prefix check

        command, *args = message_content.split()  # Uh, doesn't this break prefixes with spaces in them (it doesn't, config parser already breaks them)
        command = command[len(self.config.command_prefix):].lower().strip()

        handler = getattr(self, 'cmd_%s' % command, None)
        if not handler:
            return

        #if message.channel.is_private:
        #    if not (message.author.id == self.config.owner_id and command == 'joinserver'):
        #        await self.send_message(message.channel, 'You cannot use this bot in private messages.')
        #        return

        if message.author.id in self.blacklist and message.author.id != self.config.owner_id:
            self.safe_print("[User blacklisted] {0.id}/{0.name} ({1})".format(message.author, message_content))
            return

        else:
            self.safe_print("[Command] {0.id}/{0.name} ({1})".format(message.author, message_content))

        user_permissions = self.permissions.for_user(message.author)

        argspec = inspect.signature(handler)
        params = argspec.parameters.copy()

        # noinspection PyBroadException
        try:
            if user_permissions.ignore_non_voice and command in user_permissions.ignore_non_voice:
                await self._check_ignore_non_voice(message)

            handler_kwargs = {}
            if params.pop('message', None):
                handler_kwargs['message'] = message

            if params.pop('channel', None):
                handler_kwargs['channel'] = message.channel

            if params.pop('author', None):
                handler_kwargs['author'] = message.author

            if params.pop('server', None):
                handler_kwargs['server'] = message.server

            if params.pop('player', None):
                handler_kwargs['player'] = await self.get_player(message.channel)

            if params.pop('permissions', None):
                handler_kwargs['permissions'] = user_permissions

            if params.pop('user_mentions', None):
                handler_kwargs['user_mentions'] = list(map(message.server.get_member, message.raw_mentions))

            if params.pop('channel_mentions', None):
                handler_kwargs['channel_mentions'] = list(map(message.server.get_channel, message.raw_channel_mentions))

            if params.pop('voice_channel', None):
                handler_kwargs['voice_channel'] = message.server.me.voice_channel

            if params.pop('leftover_args', None):
                handler_kwargs['leftover_args'] = args

            args_expected = []
            for key, param in list(params.items()):
                doc_key = '[%s=%s]' % (key, param.default) if param.default is not inspect.Parameter.empty else key
                args_expected.append(doc_key)

                if not args and param.default is not inspect.Parameter.empty:
                    params.pop(key)
                    continue

                if args:
                    arg_value = args.pop(0)
                    handler_kwargs[key] = arg_value
                    params.pop(key)

            if message.author.id != self.config.owner_id:
                if user_permissions.command_whitelist and command not in user_permissions.command_whitelist:
                    raise exceptions.PermissionsError(
                        "This command is not enabled for your group (%s)." % user_permissions.name,
                        expire_in=20)

                elif user_permissions.command_blacklist and command in user_permissions.command_blacklist:
                    raise exceptions.PermissionsError(
                        "This command is disabled for your group (%s)." % user_permissions.name,
                        expire_in=20)

            if params:
                docs = getattr(handler, '__doc__', None)
                if not docs:
                    docs = 'Usage: {}{} {}'.format(
                        self.config.command_prefix,
                        command,
                        ' '.join(args_expected)
                    )

                docs = '\n'.join(l.strip() for l in docs.split('\n'))
                await self.safe_send_message(
                    message.channel,
                    '```\n%s\n```' % docs.format(command_prefix=self.config.command_prefix),
                    expire_in=60
                )
                return

            response = await handler(**handler_kwargs)
            if response and isinstance(response, Response):
                content = response.content
                if response.reply:
                    content = '%s, %s' % (message.author.mention, content)

                sentmsg = await self.safe_send_message(
                    message.channel, content,
                    expire_in=response.delete_after if self.config.delete_messages else 0,
                    also_delete=message if self.config.delete_invoking else None
                )

        except (exceptions.CommandError, exceptions.HelpfulError, exceptions.ExtractionError) as e:
            print("{0.__class__}: {0.message}".format(e))

            expirein = e.expire_in if self.config.delete_messages else None
            alsodelete = message if self.config.delete_invoking else None

            await self.safe_send_message(
                message.channel,
                '```\n%s\n```' % e.message,
                expire_in=expirein,
                also_delete=alsodelete
            )

        except exceptions.Signal:
            raise

        except Exception:
            traceback.print_exc()
            if self.config.debug_mode:
                await self.safe_send_message(message.channel, '```\n%s\n```' % traceback.format_exc())

    async def on_server_update(self, before:discord.Server, after:discord.Server):
        if before.region != after.region:
            self.safe_print("[Servers] \"%s\" changed regions: %s -> %s" % (after.name, before.region, after.region))

            await self.reconnect_voice_client(after)


if __name__ == '__main__':
    bot = MusicBot()
    bot.run()
