# This is the code for the Resident Clock Discord Bot's code
# Please ensure the following files exist and are correctly formatted so that the bot can function as intended:
###

# Resident-Clock-Config.txt         - Provides all the important mandatory data points, described on line 25
# Resident-Clock-Defaults.txt       - Default values for each server to customize defaults like what city to default the forecast command to
# Resident-Clock-Help.txt           - Contains data to print all command helpers
# Resident-Clock-Quotes.txt         - (Optional) contains an internally expandable list containing an assortment of witty quotes the bot can say


################# Import section ################


import os
import json
import datetime
import math, decimal
import random
from mee6_py_api.api import API
from mee6_py_api.utils.logging import setup_logger
import asyncio
import requests
import discord
from discord.ext import commands


#################################################

################# Setup section #################


# These are defaults for certain commands
with open('Resident-Clock-Config.txt') as json_file:
    data = json.load(json_file)
    Bot_Token = data['general'][0]['bot_token']       #bot token that belongs to the bot
    OwnerID = data['general'][1]['OwnerID']           #ID of the bot owner, used to enable a non-admin bot owner to modify bot settings
    WeatherToken = data['general'][2]['WeatherAPI']   #Token for the weather API
    AQIToken = data['general'][3]['AQI_API']          #Token for the Air Quality Index API

#Used during initialization, is used to preform a clean sweep of the "defaults" file and make sure that each server has a list of usable data
#this is done for future-proofing, to make sure that all new bot commands have their required default values consistently updated.
with open('Resident-Clock-Defaults.txt') as json_file:
    data = json.load(json_file)
    list = data['per_server']
    for idx, d in enumerate(list):
        print("checking index: " + str(idx))
        if "defaultCity" not in d.keys():
            print("defaultCity not in data, reacquiring.")
            d1 = {"defaultCity": "Victoria, CA"}
            d.update(d1)
        if "AQI_defaultCity" not in d.keys():
            print("AQI_defaultCity not in data, reacquiring.")
            d1 = {"AQI_defaultCity": "Victoria"}
            d.update(d1)
        if "Timezone" not in d.keys():
            print("Timezone not in data, reacquiring.")
            d1 = {"Timezone": 0}
            d.update(d1)
        if "ClockChannel" not in d.keys():
            print("ClockChannel not in data, reacquiring.")
            d1 = {"ClockChannel": None}
            d.update(d1)
        print("All files good, continuing-")

        data['per_server'][idx] = d
        with open('Resident-Clock-Defaults.txt', 'w') as outfile:
            json.dump(data, outfile)

#commands are not case sensitive, help command is handled by custom code. Commands are prefixed by "!"
bot = commands.Bot(command_prefix='!', help_command=None, case_insensitive=True)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!') #print this to the UI to confirm bot is functional
    await bot.change_presence(activity=discord.Game(name='with time and space')) #set the bot status
    await clocktower() #begin the clock channel update cycle

#comment this to show errors for all Discord-related issues.
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

#What to do when the bot joins a new server
@bot.event
async def on_guild_join(guild):
    #create the appropriate file set to store server-specific data
    with open('Resident-Clock-Defaults.txt') as json_file:
        data = json.load(json_file)
        newserverdefaults = {
            'serverID': guild.id,
            'defaultCity': "Victoria, CA",
            'AQI_defaultCity': "Victoria",
            'Timezone': 0,
            'ClockChannel': None
        }

        data['per_server'].append(newserverdefaults)
        with open('Resident-Clock-Defaults.txt', 'w') as outfile:
            json.dump(data, outfile)

    #Find the first accessible channel and spout the generic "Welcome message" all bots need to say for some reason.
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            await channel.send('Tick Tock! I am Resident Clock, a multi-purpose bot capable of doing all sorts of fun stuff!\nWant to get started? Use !help for a list of commands!')
            break


#################################################

############### Functions section ###############


# used to snag a default-value for each server.
def defaultGet(defaultType: str, serverID: str):
    with open('Resident-Clock-Defaults.txt') as json_file:
        data = json.load(json_file)
        list = data['per_server']
        for d in list:
            if serverID == d['serverID']:
                return d[defaultType]

# clocktower provides a service to make a channel update its name as a "clock" of sorts. Has timezone support. Each server can have a max of one of these channels.
async def clocktower():
    while True:
        now = datetime.datetime.utcnow()
        if (now.minute%5 == 0) and now.second >= 0 and now.second <= 1: #only print at the start of every 5 minute interval
            with open('Resident-Clock-Defaults.txt') as json_file:
                data = json.load(json_file)
            for x in data['per_server']:
                if x['ClockChannel'] is not None: #only attempt to write to a server's channels if a channel is selected
                    channel = bot.get_channel(x['ClockChannel']) #get the channel to write to
                    now += datetime.timedelta(hours=int(x["Timezone"])) #get the time
                    await channel.edit(name=now.strftime("Time: %-I:%M %p, %a (") + timezoneget(int(x["Timezone"])*3600) + ")") #edits the selected channel's name to get a printout of the time
                    await asyncio.sleep(299) # only run the command once every 5 minutes after a successful channel name change
        await asyncio.sleep(1) # keep pinging every second until we get a successful time change. A bit impractical, but necesarry for accurate time.

#used to efficiently grab the name of a timezone based on an hour offset
def timezoneget(offset):
    houradjusted = int(offset)/3600
    return {
        -12: "IDLW",
        -11: "NT",
        -10: "HST",
        -9: "AKST",
        -8: "PST",
        -7: "PDT",
        -6: "CST",
        -5: "EST",
        -4: "AST",
        -3: "ART",
        -2: "AT",
        -1: "WAT",
        0: "GMT",
        1: "CET",
        2: "EET",
        3: "MSK",
        4: "AMT",
        5: "PKT",
        6: "OMSK",
        7: "KRAT",
        8: "CST",
        9: "JST",
        10: "AEST",
        11: "SAKT",
        12: "NZST",
    }[int(houradjusted)]

#calculates moon position based on the date
def moonpos(dec, now=None):

   if now is None:
      now = datetime.datetime.now()

   diff = now - datetime.datetime(2001, 1, 1)
   days = dec(diff.days) + (dec(diff.seconds) / dec(86400))
   lunations = dec("0.20439731") + (days * dec("0.03386319269"))

   return lunations % dec(1)

#Generates misery
def generateUwU(input_text):
    # the length of the input text
    length = len(input_text)

    # variable declaration for the output text
    output_text = ''

    # check the cases for every individual character
    for i in range(length):

        # initialize the variables
        current_char = input_text[i]
        previous_char = '&# 092;&# 048;'

        # assign the value of previous_char
        if i > 0:
            previous_char = input_text[i - 1]

            # change 'L' and 'R' to 'W'
        if current_char == 'L' or current_char == 'R':
            output_text += 'W'

        # change 'l' and 'r' to 'w'
        elif current_char == 'l' or current_char == 'r':
            output_text += 'w'

        # if the current character is 'o' or 'O'
        # also check the previous charatcer
        elif current_char == 'O' or current_char == 'o':
            if previous_char == 'N' or previous_char == 'n' or previous_char == 'M' or previous_char == 'm':
                output_text += "yo"
            else:
                output_text += current_char

                # if no case match, write it as it is

        else:
            output_text += current_char
    output_text = output_text.replace('th', 'ff')
    output_text = output_text.replace('Th', 'Ff')
    output_text = output_text.replace('tH', 'fF')
    output_text = output_text.replace('TH', 'FF')
    #print (output_text)

    return output_text


#################################################

########## Publicly-available commands ##########


#Provides basic AQI data, takes an argument for a location
@bot.command(name='AQI')
async def cAQI(ctx, arg: str = None):

    if arg is None:
        location = defaultGet("AQI_defaultCity", ctx.message.guild.id)
    else:
        location = arg

    # call the API
    response = requests.get("https://api.waqi.info/feed/" + location + "/?token=" + AQIToken)
    #print(response.status_code)

    if response.json()["status"] == "error":
        embedVar = discord.Embed(description=("Error: Location returned no result."), color=0xFF0000)
        await ctx.send(embed=embedVar)
        return

    # json string
    json_disco = response.text
    device_disco = response.json()

    IndexValue = device_disco['data']['aqi']

    IndexValue = int(IndexValue)

    if IndexValue <= 50:
        HealthLevel = "Good"
    elif IndexValue <= 100:
        HealthLevel = "Moderate"
    elif IndexValue <= 150:
        HealthLevel = "Unhealthy for Sensitive Groups"
    elif IndexValue <= 200:
        HealthLevel = "Unhealthy"
    elif IndexValue <= 300:
        HealthLevel = "Very Unhealthy"
    elif IndexValue >= 301:
        HealthLevel = "Hazardous"

    IndexValue = str(IndexValue)

    embedVar = discord.Embed(title=(location.capitalize() + " Air Quality Index"), description=("Selected Location: " + device_disco['data']['city']['name']), color=0x404040)
    embedVar.set_thumbnail(url="https://cdn.discordapp.com/attachments/800098126693138473/800453985647460382/logo.png")
    embedVar.add_field(name="Rating: ", value=IndexValue, inline=False)
    embedVar.add_field(name="Status:", value=HealthLevel, inline=False)
    embedVar.add_field(name="᲼", value="API Data provided from [Here](https://aqicn.org/city/british-comlumbia/victoria-topaz/)", inline=False)
    await ctx.send(embed=embedVar)

#Provides basic AQI data, takes an argument for a location, is more verbose
@bot.command(name='detailed_AQI')
async def dAQI(ctx, arg: str = None):

    if arg is None:
        location = defaultGet("AQI_defaultCity", ctx.message.guild.id)
    else:
        location = arg

    # call the API
    response = requests.get("https://api.waqi.info/feed/" + location + "/?token=" + AQIToken)

    if response.json()["status"] == "error":
        embedVar = discord.Embed(description=("Error: Location returned no result."), color=0xFF0000)
        await ctx.send(embed=embedVar)
        return

    # json string
    json_disco = response.text
    device_disco = response.json()

    IndexValue = device_disco['data']['aqi']
    data = device_disco['data']


    IndexValue = int(IndexValue)

    if IndexValue <= 50:
        HealthLevel = "Good"
    elif IndexValue <= 100:
        HealthLevel = "Moderate"
    elif IndexValue <= 150:
        HealthLevel = "Unhealthy for Sensitive Groups"
    elif IndexValue <= 200:
        HealthLevel = "Unhealthy"
    elif IndexValue <= 300:
        HealthLevel = "Very Unhealthy"
    elif IndexValue >= 301:
        HealthLevel = "Hazardous"

    IndexValue = str(IndexValue)

    embedVar = discord.Embed(title=(location.capitalize() + " Air Quality Index"), description=("Selected Location:" + device_disco['data']['city']['name']), color=0x404040)
    embedVar.set_thumbnail(url="https://cdn.discordapp.com/attachments/800098126693138473/800453985647460382/logo.png")
    embedVar.add_field(name="Rating: ", value=IndexValue, inline=False)
    embedVar.add_field(name="Status:", value=HealthLevel, inline=False)
    O3Value = data['iaqi']['o3']["v"]
    PM25Value = data['iaqi']['pm25']["v"]
    NO2Value = data['iaqi']['no2']["v"]
    SO2Value = data['iaqi']['so2']["v"]
    COValue = data['iaqi']['co']["v"]
    embedVar.add_field(name="O3 Level:", value=(str(O3Value) + " μg/m3"), inline=True)
    embedVar.add_field(name="NO2 Level:", value=(str(NO2Value) + " μg/m3"), inline=True)
    embedVar.add_field(name="Fine Particulate Matter (PM2.5) Level:", value=(str(PM25Value) + " μg/m3"), inline=False)
    embedVar.add_field(name="SO2 Level:", value=(str(SO2Value) + " μg/m3"), inline=True)
    embedVar.add_field(name="CO Level:", value=(str(COValue) + " μg/m3"), inline=True)
    embedVar.add_field(name="᲼", value="More Info [Here](https://aqicn.org/city/british-comlumbia/victoria-topaz/)", inline=False)
    await ctx.send(embed=embedVar)

#Provides the time at the selected timezone. Takes an argument for a location
@bot.command(name='time')
async def time(ctx, arg: str = None):
    now = datetime.datetime.utcnow()

    if arg is None:
        location = defaultGet("defaultCity", ctx.message.guild.id)
    else:
        location = arg

    location = location.replace(" ", "") #remove spaces and such so that api call is clean

    # call the API
    response = requests.get(
        "https://api.openweathermap.org/data/2.5/forecast?q=" + location + "&%20exclude=current,minutely,hourly&cnt=1&appid=" + WeatherToken)

    if (response.json()["cod"] == "404") or (response.json()["cod"] == "429"):
        embedVar = discord.Embed(
            description=("Error Code " + response.json()["cod"] + " :\n" + response.json()["message"]), color=0xFF0000)
        await ctx.send(embed=embedVar)
        return

    now += datetime.timedelta(seconds=response.json()["city"]["timezone"])

    embedVar = discord.Embed(title=("Current Time:"), description=(now.strftime("**%-I:%M:%S %p**\n**%a, %-d/%-m/%Y**")), color=0x404040)
    embedVar.add_field(name="Location: ", value=(response.json()["city"]["name"] + "\n" + response.json()["city"]["country"]), inline=True)
    embedVar.add_field(name="Timezone:", value=(timezoneget(response.json()["city"]["timezone"]) + "\nOffset: " + str(response.json()["city"]["timezone"])), inline=True)

    await ctx.send(embed=embedVar)

#useful for checking if the bot is online, also provides a latency
@bot.command(name='ping')
async def ping(ctx):
    await ctx.send('Pong! ({0} ms)'.format(round(bot.latency, 3)))

#Stupid variation of !ping
@bot.command(name='pig')
async def pingpog(ctx):
    await ctx.send('Pog! <:Poggies:803410334437998653> ({0} ms)'.format(round(bot.latency, 3)))

#provides current temperature at the selected location. Can take an argument for the location
@bot.command(name='temperature')
async def temperature(ctx, arg: str = None):

    if arg is None:
        location = defaultGet("defaultCity", ctx.message.guild.id)
    else:
        location = arg

    # call the API
    response = requests.get(
        "https://api.openweathermap.org/data/2.5/forecast?q=" + location + "&%20exclude=current,minutely,hourly&appid=" + WeatherToken)
    # print(response.status_code)

    # jprint(response.json())

    if (response.json()["cod"] == "404") or (response.json()["cod"] == "429"):
        embedVar = discord.Embed(description=("Error Code " + response.json()["cod"] + " :\n" + response.json()["message"]), color=0xFF0000)
        await ctx.send(embed=embedVar)
        return

    # json string
    Daily = response.json()['list']
    # jprint(Daily)

    # initial print value for the forecast copypasta
    embedVar = discord.Embed(title="Today's Temperature is:", description=("Selected Location: " + str(response.json()['city']['name']) + ", " + str(response.json()['city']['country'])), color=0x404040)
    embedVar.set_thumbnail(url="https://cdn.discordapp.com/attachments/800098126693138473/800455530762076180/logo.png")


    # Gets the temperature and converts it from Kelvin to Celsius
    Temperature = str(round(int(Daily[0]['main']['temp']) - 273.15, 2))
    # Prints the temperature
    embedVar.add_field(name="Temperature: ", value=(Temperature + " °C"), inline=True)
    # Gets the feels like temperature and converts it from Kelvin to Celsius
    FeelsLike = str(round(int(Daily[0]['main']['feels_like']) - 273.15, 2))
    # Prints the feels like temperature and a new line to prepare for additional forecasts
    embedVar.add_field(name="Feels Like: ", value=(FeelsLike + " °C"), inline=True)

    embedVar.add_field(name="᲼", value="API Data provided from [Here](https://openweathermap.org/)", inline=False)
    await ctx.send(embed=embedVar)
    return

#spits out bot invite link
@bot.command(name='invite')
async def invite(ctx):
    embedVar = discord.Embed(title="Invite me to another server!", description="invite me using this [link!](https://discord.com/api/oauth2/authorize?client_id=799787945371762709&permissions=126016&scope=bot)", color=0x404040)
    embedVar.set_thumbnail(
        url="https://cdn.discordapp.com/attachments/800098126693138473/800164667489124372/big_funi.png")
    await ctx.send(embed=embedVar)

#sends a random cat picture
@bot.command(name='meow')
async def catAPI(ctx):

    # call the API
    response = requests.get("https://api.thecatapi.com/v1/images/search")

    # json string
    URL = response.json()[0]['url']

    # create an embed and set its colour
    embedVar = discord.Embed(color=0x404040)

    embedVar.set_image(url=URL)
    await ctx.send(embed=embedVar)

#sends a random dog picture
@bot.command(name='woof')
async def dogAPI(ctx):

    # call the API
    response = requests.get("https://api.thedogapi.com/v1/images/search")

    # json string
    URL = response.json()[0]['url']

    # create an embed and set its colour
    embedVar = discord.Embed(color=0x404040)

    embedVar.set_image(url=URL)
    await ctx.send(embed=embedVar)

#requires Mee6, compares XP between two users.
@bot.command(name='cmpxp')
async def compareXP(ctx, userID1 = None, userID2 = None):

    mee6API = API(ctx.guild.id)

    if userID1 == None:
        await ctx.send('Error! You must either mention the user or input their ID. Use `!help cmpxp` for a more detailed explanation.')
        return
    elif userID1.startswith('<@!'):
        userID1 = userID1.replace('<@!', '')
        userID1 = userID1.replace('>', '')

    if userID2 == None:
        userID2 = ctx.author.id
    elif userID2.startswith('<@!'):
        userID2 = userID2.replace('<@!', '')
        userID2 = userID2.replace('>', '')

    user_details = await mee6API.levels.get_user_xp(str(userID1), page_count_limit=1)
    user_details = int(user_details)
    another_user_details = await mee6API.levels.get_user_xp(str(userID2), page_count_limit=1)
    another_user_details = int(another_user_details)
    deltaXP = another_user_details - user_details
    if deltaXP > 0:
        User1Leads = True
    else:
        User1Leads = False
        deltaXP *= -1
    deltaXP = str(deltaXP)

    username1 = await bot.fetch_user(userID1)
    username2 = await bot.fetch_user(userID2)
    if User1Leads:
        embedVar = discord.Embed(title=("Comparing XP between " + username1.display_name + " and " + username2.display_name + ":"), description=("<@" + str(userID2) + ">" + " has a lead on " + "<@" + str(userID1) + ">" + " by " + deltaXP + " XP."), color=0x404040)
    else:
        embedVar = discord.Embed(title=("Comparing XP between " + username1.display_name + " and " + username2.display_name + ":"),description=("<@" + str(userID1) + ">" + " has a lead on " + "<@" + str(userID2) + ">" + " by " + deltaXP + " XP."), color=0x404040)
    await ctx.send(embed=embedVar)

#Absolute chonker of a command that can provide either a daily or a multi-day weather forecast.
@bot.command(name='forecast')
async def forecast(ctx, arg1: str = None, arg2: str = None):

    # absolute unit of a determinator to find what type of argument was added.
    SingleDay = False

    if arg1 is None and arg2 is None:
        #print("1 fired")
        SingleDay = True
        location = defaultGet("defaultCity", ctx.message.guild.id)
        dayparameter = "currentdate"
    elif (arg1 is not None) and (arg2 is None):
        #print("2 fired")
        if len(arg1) > 1:
            #print("2 1 fired")
            if any(x in arg1.lower() for x in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
                #print("2 1 1 fired")
                SingleDay = True
                location = defaultGet("defaultCity", ctx.message.guild.id)
                dayparameter = arg1
            else:
                #print("2 1 2 fired")
                SingleDay = True
                location = arg1
                dayparameter = "currentdate"
        else:
            #print("2 2 fired")
            if arg1 == 1:
                #print("2 2 1 fired")
                SingleDay = True
                location = defaultGet("defaultCity", ctx.message.guild.id)
                dayparameter = "currentdate"
            else:
                #print("2 2 2 fired")
                SingleDay = False
                location = defaultGet("defaultCity", ctx.message.guild.id)
                dayparameter = arg1
    else: #Both arguments are used
        #print("3 fired")
        if arg1.isdigit():
            #print("3 1 fired")
            if any(x in arg2.lower() for x in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
                await ctx.send("Error, you must provide either a day of the week or a number of days, but not *both*, use `!help forecast` for more information.")
                return
            if arg1 == 1:
                #print("3 1 1 fired")
                SingleDay = True
                location = arg2
                dayparameter = "currentdate"
            else:
                #print("3 1 2 fired")
                SingleDay = False
                location = arg2
                dayparameter = arg1
        elif arg2.isdigit():
            #print("3 2 fired")
            if any(x in arg1.lower() for x in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
                await ctx.send("Error, you must provide either a day of the week or a number of days, but not *both*, use `!help forecast` for more information.")
                return
            if arg2 == 1:
                #print("3 2 1 fired")
                SingleDay = True
                location = arg1
                dayparameter = "currentdate"
            else:
                #print("3 2 2 fired")
                SingleDay = False
                location = arg1
                dayparameter = arg2
        elif any(x in arg1.lower() for x in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
            #print("3 3 fired")
            SingleDay = True
            dayparameter = arg1
            location = arg2
        else: #arg2.lower == ("monday" or "tuesday" or "wednesday" or "thursday" or "friday" or "saturday" or "sunday"):
            #print("3 4 fired")
            SingleDay = True
            dayparameter = arg2
            location = arg1



    #remove spaces so that country codes don't have to look like trash when you input them
    location = location.replace(" ", "")
    dayparameter = str(dayparameter)
    dayparameter = dayparameter.replace(" ", "")

    # call the API
    response = requests.get("https://api.openweathermap.org/data/2.5/forecast?q=" + location + "&%20exclude=current,minutely,hourly&appid=" + WeatherToken)

    if (response.json()["cod"] == "404") or (response.json()["cod"] == "429"):
        embedVar = discord.Embed(description=("Error Code " + response.json()["cod"] + " :\n" + response.json()["message"]), color=0xFF0000)
        await ctx.send(embed=embedVar)
        return

    # json string
    Timezone = response.json()['city']['timezone']
    Daily = response.json()['list']

    if SingleDay is False:

        dayparameter = int(dayparameter)
        if dayparameter < 1:
            dayparameter = 1
        if dayparameter > 5:
            dayparameter = 5

        # initial print value for the forecast copypasta
        embedVar = discord.Embed(title="The forecast for the next " + str(dayparameter) + " days in " + str(response.json()['city']['name']) + " is:", description=("Selected Location: " + str(response.json()['city']['name']) + ", " + str(response.json()['city']['country'])), color=0x404040)
        embedVar.set_thumbnail(url="https://cdn.discordapp.com/attachments/800098126693138473/800455530762076180/logo.png")

        thing = True
        currentday = 0
        # cycles through today and the next 7 days to get all the forecast data in
        for d in Daily:
            # grabbing the date from the API
            epoch_time = d['dt'] + Timezone
            Date = datetime.datetime.fromtimestamp(epoch_time)

            if (any(x in str(Date.hour) for x in ['11', '12', '13'] or thing == True) and currentday < dayparameter):

                thing = False
                currentday += 1

                # gets the current weather description
                WeatherDesc = str(d['weather'][0]['description'])
                # finds the correct Emoji to use
                ID = str(d['weather'][0]["icon"])
                Emoji = ":face_with_symbols_over_mouth:"
                if ID == "01d":
                    # Clear Day
                    Emoji = ":sunny:"
                if ID == "01n":
                    # Clear Night
                    Emoji = ":new_moon:"
                if ID == "02d":
                    # few clouds
                    Emoji = ":white_sun_small_cloud:"
                if ID == "02n":
                    # few clouds
                    Emoji = ":white_sun_small_cloud:"
                if ID == "03d":
                    # scattered clouds
                    Emoji = ":white_sun_cloud:"
                if ID == "03n":
                    # scattered clouds
                    Emoji = ":white_sun_cloud:"
                if ID == "04d":
                    # overcast
                    Emoji = ":cloud:"
                if ID == "04n":
                    # overcast
                    Emoji = ":cloud:"
                if ID == "09d":
                    # showers
                    Emoji = ":cloud_rain:"
                if ID == "09n":
                    # showers
                    Emoji = ":cloud_rain:"
                if ID == "10d":
                    # rain
                    Emoji = ":white_sun_rain_cloud:"
                if ID == "10n":
                    # rain
                    Emoji = ":white_sun_rain_cloud:"
                if ID == "11d":
                    # thunder
                    Emoji = ":thunder_cloud_rain:"
                if ID == "11n":
                    # thunder
                    Emoji = ":thunder_cloud_rain:"
                if ID == "13d":
                    # snow
                    Emoji = ":cloud_snow:"
                if ID == "13n":
                    # snow
                    Emoji = ":cloud_snow:"
                if ID == "50d":
                    # fog
                    Emoji = ":fog:"
                if ID == "50n":
                    # fog
                    Emoji = ":fog:"

                Title = (Date.strftime("%A, %b %#d: ") + Emoji)
                # Prints Emoji and Weather Description Values
                Desc = ("Weather:   " + WeatherDesc + '\n')
                # Gets the temperature and converts it from Kelvin to Celsius
                Temperature = str(round(int(d['main']['temp']) - 273.15, 2))
                # Prints the temperature
                Desc += ("Temp: " + Temperature + " °C" + '\n')
                # Gets the feels like temperature and converts it from Kelvin to Celsius
                FeelsLike = str(round(int(d['main']['feels_like']) - 273.15, 2))
                # Prints the feels like temperature and a new line to prepare for additional forecasts
                Desc += (
                            "Feels like: " + FeelsLike + " °C")
                embedVar.add_field(name=Title, value=Desc, inline=True)

        embedVar.add_field(name="᲼", value="API Data provided from [Here](https://openweathermap.org/)", inline=False)
        await ctx.send(embed=embedVar)

    if SingleDay is True:

        dayparameter = dayparameter.lower()
        # json string
        Daily = response.json()['list']
        Timezone = response.json()['city']['timezone']

        isdaytoday = False

        # initial print value for the forecast copypasta
        if (dayparameter == "currentdate"):
            isdaytoday = True
            Now = datetime.datetime.now()
            Now += datetime.timedelta(seconds= Timezone)
            dayparameter = Now.strftime("%A")

        currentday = 0
        DayWasFound = False
        # cycles through today and the next 7 days to get all the forecast data in
        for d in Daily:
            # grabbing the date from the API
            epoch_time = d['dt'] - Timezone
            Date = datetime.datetime.fromtimestamp(epoch_time)
            if (dayparameter.lower() == Date.strftime("%A").lower()):
                if DayWasFound is False and isdaytoday is False:
                    embedVar = discord.Embed(title=Date.strftime("The forecast for %A, %b %#d, in ") + str(response.json()['city']['name']) + " is:", description=("Selected Location: " + str(response.json()['city']['name']) + ", " + str(response.json()['city']['country'])), color=0x404040)
                    embedVar.set_thumbnail(url="https://cdn.discordapp.com/attachments/800098126693138473/800455530762076180/logo.png")
                DayWasFound = True
                currentday += 1
                # printing the date
                # gets the current weather description
                WeatherDesc = str(d['weather'][0]['description'])
                # finds the correct Emoji to use
                ID = str(d['weather'][0]["icon"])
                Emoji = ":face_with_symbols_over_mouth:"
                if ID == "01d" or ID == "01n":
                    # Clear Day/Night
                    if Date.hour > 7 and Date.hour < 18:
                        Emoji = ":sunny:"
                    else:
                        Emoji = ":new_moon:"
                if ID == "02d":
                    # few clouds
                    Emoji = ":white_sun_small_cloud:"
                if ID == "02n":
                    # few clouds
                    Emoji = ":white_sun_small_cloud:"
                if ID == "03d":
                    # scattered clouds
                    Emoji = ":white_sun_cloud:"
                if ID == "03n":
                    # scattered clouds
                    Emoji = ":white_sun_cloud:"
                if ID == "04d":
                    # overcast
                    Emoji = ":cloud:"
                if ID == "04n":
                    # overcast
                    Emoji = ":cloud:"
                if ID == "09d":
                    # showers
                    Emoji = ":cloud_rain:"
                if ID == "09n":
                    # showers
                    Emoji = ":cloud_rain:"
                if ID == "10d":
                    # rain
                    Emoji = ":white_sun_rain_cloud:"
                if ID == "10n":
                    # rain
                    Emoji = ":white_sun_rain_cloud:"
                if ID == "11d":
                    # thunder
                    Emoji = ":thunder_cloud_rain:"
                if ID == "11n":
                    # thunder
                    Emoji = ":thunder_cloud_rain:"
                if ID == "13d":
                    # snow
                    Emoji = ":cloud_snow:"
                if ID == "13n":
                    # snow
                    Emoji = ":cloud_snow:"
                if ID == "50d":
                    # fog
                    Emoji = ":fog:"
                if ID == "50n":
                    # fog
                    Emoji = ":fog:"

                Title = (Date.strftime("%-I:%M %p: ") + Emoji)
                # Prints Emoji and Weather Description Values
                Desc = ("Weather:   " + WeatherDesc + '\n')
                # Gets the temperature and converts it from Kelvin to Celsius
                Temperature = str(round(int(d['main']['temp']) - 273.15, 2))
                # Prints the temperature
                Desc += ("Temp: " + Temperature + " °C" + '\n')
                # Gets the feels like temperature and converts it from Kelvin to Celsius
                FeelsLike = str(round(int(d['main']['feels_like']) - 273.15, 2))
                # Prints the feels like temperature and a new line to prepare for additional forecasts
                Desc += ("Feels like: " + FeelsLike + " °C")
                embedVar.add_field(name=Title, value=Desc, inline=True)

        if DayWasFound is True:
            embedVar.add_field(name="᲼", value="API Data provided from [Here](https://openweathermap.org/)", inline=False)
            await ctx.send(embed=embedVar)
        else:
            await ctx.send("Specified Day out of Range, please try a different day, use `!help forecast` for more information.")

#generator to print all or specific help commands
@bot.command(name='help')
async def help(ctx, arg: str = None):
    with open('Resident-Clock-Help.txt') as json_file:
        data = json.load(json_file)
    if arg is None:
        embedVar = discord.Embed(title="Resident cLock Commands List", color=0xFFFF00)
        embedVar.set_thumbnail(url="https://cdn.discordapp.com/attachments/800098126693138473/800164667489124372/big_funi.png")
        for d in data['list']:
            embedVar.add_field(name=("!" + d["id"]), value=d["Description"],inline=False)
        await ctx.send(embed=embedVar)
    else:
        for d in data["list"]:
            if arg.lower() == str(d["id"]).lower():
                embedVar = discord.Embed(title=("Help - " + d["Name"]), color=0xFFFF00)
                embedVar.add_field(name="Description:", value=d["DetailedDesc"], inline=False)
                embedVar.add_field(name="Usage:", value=d["Usage"], inline=False)
                embedVar.add_field(name="Example:", value=d["Example"], inline=False)
                embedVar.set_image(url=d["Image"])
                await ctx.send(embed=embedVar)
                return
        embedVar = discord.Embed(description="The command you've entered could not be found.", color=0xFF0000)
        await ctx.send(embed=embedVar)

#Bot will spit out a random quote from a list of supplied quotes from "Resident-Clock-Quotes.txt"
@bot.command(name='quote')
async def quote(ctx):
    with open('Resident-Clock-Quotes.txt', "r") as json_file:
        data = json.load(json_file)
        temp = data['quotes']
        quotenum = len(temp)
        index = random.randint(1, quotenum)
        await ctx.send(temp[index-1][str(index)])

#Provides the currrent moon phase along with an emote
@bot.command(name='moonie')
async def moonie(ctx):
    dec = decimal.Decimal

    pos = moonpos(dec)
    index = (pos * dec(8)) + dec("0.5")
    roundedpos = round(float(pos), 3)
    index = math.floor(index)
    index = int(index)
    if index == 8:
        index = 0

    embedVar = discord.Embed(title="Current Moon Phase", color=0x404040)

    if index == 0:
        embedVar.set_thumbnail(url="https://cdn.discordapp.com/attachments/803372407133962251/803380642891956324/new-moon_1f311.png")
        embedVar.add_field(name="New Moon", value=("position: " + str(roundedpos)), inline=False)
    elif index == 1:
        embedVar.set_thumbnail(url="https://cdn.discordapp.com/attachments/803372407133962251/803380679379124244/waxing-crescent-moon_1f312.png")
        embedVar.add_field(name="Waxing Crescent", value=("position: " + str(roundedpos)), inline=False)
    elif index == 2:
        embedVar.set_thumbnail(url="https://cdn.discordapp.com/attachments/803372407133962251/803380815592816670/first-quarter-moon_1f313.png")
        embedVar.add_field(name="First Quarter", value=("position: " + str(roundedpos)), inline=False)
    elif index == 3:
        embedVar.set_thumbnail(url="https://cdn.discordapp.com/attachments/803372407133962251/803380906005495818/waxing-gibbous-moon_1f314.png")
        embedVar.add_field(name="Waxing Gibbous", value=("position: " + str(roundedpos)), inline=False)
    elif index == 4:
        embedVar.set_thumbnail(url="https://cdn.discordapp.com/attachments/803372407133962251/803380926306189333/full-moon_1f315.png")
        embedVar.add_field(name="Full Moon", value=("position: " + str(roundedpos)), inline=False)
    elif index == 5:
        embedVar.set_thumbnail(url="https://cdn.discordapp.com/attachments/803372407133962251/803380946149703730/waning-gibbous-moon_1f316.png")
        embedVar.add_field(name="Waning Gibbous", value=("position: " + str(roundedpos)), inline=False)
    elif index == 6:
        embedVar.set_thumbnail(url="https://cdn.discordapp.com/attachments/803372407133962251/803380969310650378/last-quarter-moon_1f317.png")
        embedVar.add_field(name="Last Quarter", value=("position: " + str(roundedpos)), inline=False)
    elif index == 7:
        embedVar.set_thumbnail(url="https://cdn.discordapp.com/attachments/803372407133962251/803380991019188244/waning-crescent-moon_1f318.png")
        embedVar.add_field(name="Waning Crescent", value=("position: " + str(roundedpos)), inline=False)
    await ctx.send(embed=embedVar)


#################################################

################ Cursed Commands ################


#A mistake
@bot.command(name='quwute')
async def cursed_quote(ctx):
    with open('Resident-Clock-Quotes.txt') as json_file:
        data = json.load(json_file)
        temp = data['quotes']
        quotenum = len(temp)
        index = random.randint(1, quotenum)
        text = generateUwU(temp[index-1][str(index)])
        await ctx.send(text)

#A The greatest mistake of all
@bot.command(name='uwu')
async def cursedspeak(ctx, *, arg):
    userid = ctx.author.id
    await ctx.send("<@" + str(userid) + "> <:NervousFingies:805327321502449685> "  + generateUwU(arg) + " uwu")

#A mistake
@bot.command(name='hewp')
async def hewp(ctx, arg: str = None):
    with open('Resident-Clock-Help.txt') as json_file:
        data = json.load(json_file)
    if arg is None:
        embedVar = discord.Embed(title=generateUwU("Resident cLock Commands List"), color=0xFFFF00)
        embedVar.set_thumbnail(url="https://cdn.discordapp.com/attachments/800098126693138473/800164667489124372/big_funi.png")
        for d in data['list']:
            embedVar.add_field(name=("!" + d["id"]), value=generateUwU(d["Description"]),inline=False)
        await ctx.send(embed=embedVar)
    else:
        for d in data["list"]:
            if arg.lower() == str(d["id"]).lower():
                embedVar = discord.Embed(title=("Hewp - " + generateUwU(d["Name"])), color=0xFFFF00)
                embedVar.add_field(name=generateUwU("Description:"), value=generateUwU(d["DetailedDesc"]), inline=False)
                embedVar.add_field(name=generateUwU("Usage:"), value=generateUwU(d["Usage"]), inline=False)
                embedVar.add_field(name=generateUwU("Example:"), value=generateUwU(d["Example"]), inline=False)
                embedVar.set_image(url=d["Image"])
                await ctx.send(embed=embedVar)
                return
        embedVar = discord.Embed(description=generateUwU("The command you've entered could not be found."), color=0xFF0000)
        await ctx.send(embed=embedVar)


#################################################

############## Admin-only commands ##############


#Admin-only command. Allows the user to modify the server's default values for things such as forecast, time, etc.
@bot.command(name='changedefault')
async def changedefault(ctx, defaultType, newDefault):
    if defaultType is None:
        await ctx.send("You need to provide what argument you want to change *and* the new value")
        return
    if defaultType == "serverID":
        await ctx.send("No one is permitted to alter this value, as it would compromise bot functionality.")
        return
    # This command will allow admins to set the timezone and channel to update for the bot's clock function
    if (str(ctx.message.author.id) == str(OwnerID)) or (ctx.message.author.mention == discord.Permissions.administrator):
        with open('Resident-Clock-Defaults.txt') as json_file:
            data = json.load(json_file)
        for idx, d in enumerate(data['per_server']):
            if d['serverID'] == ctx.message.guild.id:
                if defaultType not in data['per_server'][idx]:
                    ctx.send("Invalid Default Type, this is not a type that exists.")
                else:
                    temp = data['per_server'][idx][defaultType]
                    data['per_server'][idx][defaultType] = newDefault
        with open('Resident-Clock-Defaults.txt', 'w') as outfile:
            json.dump(data, outfile)
        embedVar = discord.Embed(title="Default Value Altered:", description=("**" + defaultType + "**\nOld: " + temp + "\nNew: " + str(newDefault)), color=0x02f513)
        await ctx.send(embed=embedVar)
        return
    else:
        ctx.send("You lack the required permissions to change these settings. Please contact an Admin for help.")
        return

#Requires Admin, enables assignment of a clocktower channel
@bot.command(name="clocktower")
async def assigntime(ctx, channelID, offset):
    #This command will allow admins to set the timezone and channel to update for the bot's clock function
    if (str(ctx.message.author.id) == str(OwnerID)) or (ctx.message.author.mention == discord.Permissions.administrator):
        with open('Resident-Clock-Defaults.txt') as json_file:
            data = json.load(json_file)
        print("file opened, proceeding to check server lists")
        for idx, d in enumerate(data['per_server']):
            #print(d['serverID'])
            #print(ctx.message.guild.id)
            if d['serverID'] == ctx.message.guild.id:
                data['per_server'][idx]['Timezone'] = offset
                if channelID.lower() == "none":
                    data['per_server'][idx]['ClockChannel'] = None
                else:
                    data['per_server'][idx]['ClockChannel'] = channelID
        with open('Resident-Clock-Defaults.txt', 'w') as outfile:
            json.dump(data, outfile)
            print("wrote to file")
        embedVar = discord.Embed(title="Added Clock Tower:", description=(str(channelID) + ", " + str(offset)), color=0x02f513)
        await ctx.send(embed=embedVar)
    else:
        ctx.send("You lack the required permissions to change these settings. Please contact an Admin for help.")


#################################################

############## Owner-only commands ##############


#Owner-only command. Used as a security precaution. Prints all servers the bot is in.
@bot.command(name='serverlist')
async def servers(ctx):
    if str(ctx.message.author.id) == str(OwnerID):
        activeservers = bot.guilds
        description = ""
        for guild in activeservers:
            description += (guild.name + "\n")
            #print(guild)
            #print(guild.name + ": " + guild.id)
        embedVar = discord.Embed(title="Here is a list of all servers that I am a member of:", description=description, color=0x404040)
        await ctx.send(embed=embedVar)

#Owner-only command. Allows the bot to remotely leave a server without the owner necesarrily sharing the server with the bot
@bot.command(name='emergencyleave')
async def emergencykick(ctx, *, guild_name):
    if str(ctx.message.author.id) == str(OwnerID):
        guild = discord.utils.get(bot.guilds, name=guild_name)
        if guild is None:
            await ctx.send("I don't recognize that guild.")
            return
        await bot.http.leave_guild(guild_id=guild.id)
        await ctx.send(f":ok_hand: Left guild: {guild.name} ({guild.id})")

#Owner-only command. Enables the bot owner to speak through the bot. The bot will take the given input, delete the original message, and echo what it said.
@bot.command(name='speak')
async def speak(ctx, *, arg):
    if str(ctx.message.author.id) == str(OwnerID):
        await ctx.message.delete()
        await ctx.send(arg)
    else:
        await ctx.send("nice try pal")

#Owner-only command. Adds a quote that the bot can use
@bot.command(name='q_add')
async def quoteadd(ctx, *, arg):
    if str(ctx.message.author.id) == str(OwnerID):
        with open('Resident-Clock-Quotes.txt') as json_file:
            data = json.load(json_file)
            temp = data['quotes']
            quotenum = len(temp)
            quote = {
                (quotenum + 1): arg
            }
            data['quotes'].append(quote)
            with open('Resident-Clock-Quotes.txt', 'w') as outfile:
                json.dump(data, outfile)
        embedVar = discord.Embed(title="Quote added:", description=(arg), color=0x02f513)
        await ctx.send(embed=embedVar)
    else:
        await ctx.send("nice try pal")


#################################################

############ Yoda Punishment Section ############


@bot.command(name='show_add')
async def showadd(ctx, *, arg):
    if (str(ctx.message.author.id) == str(OwnerID)) or (str(ctx.message.author.id) == str(381312702871764992)):
        with open('ShowListRef.txt') as json_file:
            data = json.load(json_file)
        toAppend = {
            ('name'): arg
        }
        data['show'].append(toAppend)
        with open('ShowListRef.txt', 'w') as outfile:
            json.dump(data, outfile)
        embedVar = discord.Embed(title="Show added:", description=(arg), color=0x02f513)
        await ctx.send(embed=embedVar)
    else:
        await ctx.send("nice try pal")

@bot.command(name='show_list')
async def show_list(ctx):
    with open('ShowList.txt') as json_file:
        data = json.load(json_file)
    description = ""
    for d in data['show']:
        print(d['name'])
        description += (d['name'] + '\n')
    embedVar = discord.Embed(title="List of Shows Yoda Must Watch:", description="Number of disappointments: " + str(data['tally']) + '\n\n' + description, color=0xFFFF00)
    await ctx.send(embed=embedVar)

@bot.command(name='disappointment')
async def disappointment(ctx):
    if (str(ctx.message.author.id) == str(OwnerID)) or (str(ctx.message.author.id) == str(381312702871764992)):
        with open('ShowlistRef.txt') as json_file:
            data = json.load(json_file)
            temp = data['show']
            index1 = random.randint(0, (len(temp)-1))
            show = {
                "name": temp[index1]['name']
            }
            del data['show'][index1]
            with open('ShowlistRef.txt', 'w') as outfile:
                json.dump(data, outfile)
        with open('Showlist.txt') as json_file:
            data = json.load(json_file)
            data['show'].append(show)
            temp = int(data['tally']) + 1
            data['tally'] = temp
            with open('Showlist.txt', 'w') as outfile:
                json.dump(data, outfile)
        embedVar = discord.Embed(title="Show added to Queue:", description=show['name'], color=0x02f513)
        await ctx.send(embed=embedVar)
    else:
        await ctx.send("nice try pal")


#################################################


bot.run(Bot_Token) #The greatest demonstration that size doesn't matter