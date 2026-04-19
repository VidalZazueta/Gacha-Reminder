# Gacha-Reminder
## Description
A discord bot to remind users about the current events in their favorite gacha game. As more gacha games continue to release very year, it becomes increasingly harder manage several different gacha games. Many of these gacha games have to be launched through their own service, so logging in to see what events are available will take a couple of minutes. Adding multiple games on top of this and it becomes harder to manage what game you want to play so you don't miss out on any events.

## Goal
The goal of this project is to create a discord bot to give users consistent reminders about the current events in their favorite gacha games. Showing users what events are available and what events will end soon will help them manage their time and prioritize the right game.

## Current Progress
Supports fetching and displaying currently ongoing in-game events for Wuthering Waves and Zenless Zone Zero. Events are sourced from their respective Fandom wikis via the MediaWiki Action API, parsed from wikitext templates, and displayed as Discord embeds with game thumbnails and time-remaining countdowns.

## Project Structure
```
Gacha-Reminder/
├── main.py               Entry point — bot setup and command registration
├── api/
│   └── wiki_api.py       MediaWiki API client and event parsing logic
├── config/
│   └── config.py         Credentials, API URLs, and per-game metadata
├── embeds/
│   └── embeds.py         Reusable Discord embed factory functions
├── commands/
│   ├── game_commands.py  User-facing slash commands (/events_wuwa, /events_zzz, etc.)
│   └── dev_commands.py   Developer/diagnostic slash commands
└── images/               Game thumbnail assets
```

## Slash Commands
| Command | Description |
|---|---|
| `/events_wuwa`    | Current Wuthering Waves events with thumbnail |
| `/events_zzz`     | Current Zenless Zone Zero events with thumbnail |
| `/events_all`     | Events from all supported games in one embed |
| `/events_timed`   | Wuthering Waves events with fetch/process timing stats |

## Technologies Used
Python  
Visual Studio Code or any text editor

## Packages
discord.py  
python-dotenv  
aiohttp

## Planned Features
Filtering by event type (In-Game vs Web events)  
Showing upcoming events (starting soon)  
Support for additional gacha games  
  



