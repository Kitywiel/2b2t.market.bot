@echo off
title 2b2t Market Bot
:start
echo Starting bot...
python bot.py
echo Bot crashed or stopped. Restarting in 5 seconds...
timeout /t 5
goto start
