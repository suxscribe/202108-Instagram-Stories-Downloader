import configparser
import os
import instaloader
from instaloader.lateststamps import LatestStamps
from configparser import ConfigParser
from datetime import datetime
import pytz

import telebot
from telethon.sync import TelegramClient
from telethon.tl.types import InputPeerUser, InputPeerChannel
from telethon import TelegramClient, sync, events

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

config = ConfigParser()

# make config if not created
configFile = "config.ini"
configPath = os.path.join(os.getcwd(), configFile)
if not os.path.isfile(configPath):
    file = open(configFile, "w")
    file.close()

config.read(configFile)
if not "main" in config.sections():
    initDate = str(datetime.datetime(1970, 1, 1))
    config.add_section("main")
    config.set("main", "latestUpload", initDate)
    with open("config.ini", "w") as f:
        config.write(f)


# Instaloader Stuff
L = instaloader.Instaloader(
    filename_pattern="{profile}/{date_utc:%Y-%m-%d}/{profile}---{date_utc}---UTC_{typename}",
    save_metadata=False,
)

latestStamp = LatestStamps("./latest-stamps.ini")

USER = config.get("config", "igUSER")
PASSWORD = config.get("config", "igPASS")

userIds = [19208572604]  # sdr.face
userNames = ["sdr.face"]
profiles = {"kornilova.sdr": 26791128260, "sdr.face": 19208572604}

# Optionally, login or load session
# L.login(USER, PASSWORD)        # (login)
# L.interactive_login(USER)      # (ask password on terminal)

logged = False

try:
    L.load_session_from_file(USER)  # (load session created `instaloader -l USERNAME`)
    logged = True
# except:
#     L.login(USER, PASSWORD)
#     logged = True
except:
    print("login failed")
    logged = False

if logged == True:

    # profile = L.check_profile_id("sdr.face")

    # get story latest date
    # for story in L.get_stories(userids=userIds):
    #    print("story latest date: " + str(story.latest_media_utc))
    # download single story items one by one
    # for item in story.get_items():
    #     # print(item)
    #     # L.format_filename(item)
    #     L.download_storyitem(item, "stories_py")  # only checks if file exists

    # download stories
    L.download_stories(
        userids=list(profiles.values()),
        fast_update=False,
        filename_target="stories",
        storyitem_filter=None,
        latest_stamps=latestStamp,
    )

    # print latest timestamp
    # for name in userNames:
    #    print("latest stamp: " + str(latestStamp.get_last_story_timestamp(name)))


path = os.path.join(os.getcwd(), "stories")
filetypes = [".jpg", ".png", ".webp", ".gif", ".mp4"]

profileFilesToSend = {}


# scan folders and files in 'stories' folder. process each folder individually. profile by profile

# print(path)
if os.path.isdir(path):
    # print(os.listdir(path))

    for profileDir in os.listdir(path):
        profilePath = os.path.join(path, profileDir)
        # print(profilePath)

        filesToSend = {}
        # in profile folder process dates folders. each date - separate message.
        for dateDir in os.listdir(profilePath):
            datePath = os.path.join(profilePath, dateDir)

            # print(os.listdir(datePath))

            fileList = []

            for file in os.listdir(datePath):
                filePath = os.path.join(datePath, file)
                if os.path.isfile(filePath):
                    # print(file)

                    # get only media files from date folder and send it to telegram
                    ext = os.path.splitext(file)[1]
                    if ext.lower() in filetypes:
                        # print("sending file")
                        # add file to filesToSend list
                        fileList.append(file)

                    else:
                        print("skipping file")

            filesToSend[dateDir] = fileList

        profileFilesToSend[profileDir] = filesToSend

print(profileFilesToSend)

# make 'latest_uploaded' config file. Initial - no date. Then get latestStamp and process found files with date in filename until the latestStamp. Stop at latestStamp. Set 'latest_uploaded' to latestStamp
# if no 'latest uploaded' file - create one. with no date
# set 'latest uploaded' to latestStamp after successful upload


latestUpload = config.get("main", "latestUpload")

print(latestUpload)

utc = pytz.UTC
latestUploadDate = datetime.strptime(latestUpload, DATETIME_FORMAT)

latestUploadDate = utc.localize(latestUploadDate)  # convert to utc for camparison

# check filenames in filesToSend list from 'latest uploaded' date up to latestStamp for this profile

for name in profiles:
    # todo add user profiles level in filesToSend dict
    latestStampDate = latestStamp.get_last_story_timestamp(profiles[name])

    if latestUploadDate < latestStampDate:
        for date in filesToSend:  # upload, change latest Uploaded
            # print(date)
            for file in filesToSend[date][:]:
                # print(file)

                fileDate = file.split("---")[1]

                fileDate = datetime.strptime(fileDate, "%Y-%m-%d_%H-%M-%S")
                fileDate = utc.localize(fileDate)
                # print(fileDate)

                if (
                    latestUploadDate > fileDate
                ):  # remove file from list if older than last upload
                    print("removing " + file)
                    filesToSend[date].remove(file)

                # todo get date from filename. if date > latestUploadDate -> upload
                # else -> delete from list
    else:  # do nothing
        filesToSend = {}
        print("skipping upload. everything's up to date")


# TELEGRAM PART
# get your api_id, api_hash, token
# from telegram as described above
api_id = config.get("config", "tgApiId")
api_hash = config.get("config", "tgApiHash")
token = config.get("config", "tgApiToken")
message = "Working..."

# your phone number
phone = config.get("config", "tgPhone")

# creating a telegram session and assigning
# it to a variable client
client = TelegramClient("session", api_id, api_hash)

# connecting and building the session
client.connect()

# in case of script ran first time it will
# ask either to input token or otp sent to
# number or sent or your telegram id
if not client.is_user_authorized():

    client.send_code_request(phone)

    # signing in the client
    client.sign_in(phone, input("Enter the code: "))

try:

    # destination_user_username or channel
    destination_channel_id = config.get("config", "tgChannel")
    entity = client.get_entity(destination_channel_id)

    # sending message using telegram client
    for date in filesToSend:

        fileAlbum = []
        albumCaption = userNames[0] + ": " + date
        for file in filesToSend[date]:
            fileAlbum.append(
                os.path.join(os.getcwd(), "stories", userNames[0], date, file)
            )

        # print(fileAlbum)
        # client.send_message(
        #     entity, str(filesToSend[date]), parse_mode="html"
        # )  # "me" works

        client.send_file(entity, fileAlbum, caption=userNames[0] + ": " + date)

    uploaded = True

except Exception as e:

    uploaded = False

    # there may be many error coming in while like peer
    # error, wwrong access_hash, flood_error, etc
    print(e)

# disconnecting the telegram session
client.disconnect()

# UPDATE LAST TIMESTAMP
# todo add multiprofile
if uploaded == True:
    latestUploadDate = datetime.strftime(
        latestStamp.get_last_story_timestamp(userNames[0]), DATETIME_FORMAT
    )  # update latest upload
    config.set("main", "latestUpload", str(latestUploadDate))
    with open("config.ini", "w") as f:
        config.write(f)


# print(filesToSend)
