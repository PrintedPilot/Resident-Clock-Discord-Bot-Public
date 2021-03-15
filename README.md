Resident-Clock-Discord-Bot

This Discord bot relies on several important files imperative to its functionality, these will be explained below:

Resident-Clock-Config.txt:
	
	Resident Clock Config is a small file used to store the bot's key components of data. This config file is set up by the user and is not modified
	by the bot itself.

	- The "bot token" section is where you put your bot's token, this is necesarry for Discord to know what bot to connect your program to
	- The "OwnerID" section is for the bot owner's Discord UserID, which enables them to do several things including overriding admin control,
          removing the bot from servers remotely, and much more. It's used as a means for the owner to retain complete control over the bot no matter
	  the scenerio.
	- The "WeatherAPI" and "AQI_API" slots are both for API keys for their respective services.
		WeatherAPI requires an API key from OpenWeatherMap.org
		AQI_API requires an API key from aqicn.org

Resident-Clock-Defaults.txt:
	
	Resident Clock Defaults is a file utilized by the bot to store a variety of server-specific sets of data. This file requires no user input, and is
	entirely handled by the bot. When the bot joins a server, it automatically creates a new section in the "per server" list, where it can then store 
	data that the server uses, This is done in order to enable each server to have its own set of defaults such as default forecast location or default
	timezone. These values can be changed using the "changedefault" command, available to admins and the bot owner.

Resident-Clock-Help.txt:

	Resident Clock Help contains a list that documents each command's functionality, and includes several sections in each element in the list which are
	used as a means to generate help commands should the user require assistance. Modifying the text in this file will directly influence the output 	 	that the bot provides to a user, when they call "!help <command name>"

Resident-Clock-Quotes.txt:

	Used by the bot to call upon a bunch of random phrases or 'famous quotes' to give it a bit more personality. The bot will randomly select one of the
	quotes available in this file, and say it when a user calls "!quote". Note that it is not recommended to modify this file outside of Discord, as the
	more simple option is to use the "!q_add" command provided to the bot owner. For example, if I want the bot to be able to say "Tick Tock on the Clock"
	then the owner can input "!q_add Tick Tock on the Clock"

requirements.txt, Procfile, and runtime.txt are all files used by Heroku as of this time in order to deploy it. These files may change in the future
when a better hosting service is applied to the bot.