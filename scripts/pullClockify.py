# imports
import requests
import pymongo
from dotenv import load_dotenv
import os
import pandas as pd

# settings.py
load_dotenv()
clockify_api_key = os.getenv("CLOCKIFY_API_KEY")
mongo_conn_string = os.getenv("MONGO_CONN")

headers = {"Accept": "application/json", 'x-api-key': clockify_api_key}


def GetTags():
    print('Waiting on Clockify API for Tags')
    tags_url = "https://api.clockify.me/api/v1/workspaces/5f25e65aadbc875dd9032dee/tags"
    tags = requests.get(tags_url, headers=headers)
    tags = tags.json()
    #   rename keys, remove unneeded keys
    for t in tags:
        t['tag_id'] = t['id']
        t['tag_name'] = t['name']
        del t['id']
        del t['name']
        del t['workspaceId']
        del t['archived']
    print('Tags received\n')
    return tags


def GetProjects():
    print('Waiting on Clockify API for Projects')
    projects_url = "https://api.clockify.me/api/v1/workspaces/5f25e65aadbc875dd9032dee/projects"
    projects = requests.get(projects_url, headers=headers)
    projects = projects.json()
    #   rename keys, remove unneeded keys
    for p in projects:
        p['project_id'] = p['id']
        p['project'] = p['name']
        p['project_duration'] = p['duration']
        del p['id']
        del p['duration']
        del p['name']
        del p['hourlyRate']
        del p['clientId']
        del p['workspaceId']
        del p['billable']
        del p['memberships']
        del p['color']
        del p['estimate']
        del p['archived']
        del p['clientName']
        del p['note']
        del p['template']
        del p['public']
    print('Projects received\n')
    return projects


def GetEntries():
    print('Waiting on Clockify API for Entries')
    entries_url = "https://api.clockify.me/api/v1/workspaces/5f25e65aadbc875dd9032dee/user/5f25e659adbc875dd9032ded/time-entries"
    entries = requests.get(entries_url, headers=headers)
    entries = entries.json()
    #   rename keys, remove unneeded keys
    for e in entries:
        e['entry_id'] = e['id']
        e['entry_start'] = e['timeInterval']['start']
        e['entry_finish'] = e['timeInterval']['end']
        e['entry_duration'] = e['timeInterval']['duration']
        e['entry'] = e['description']
        e['tags'] = []
        del e['id']
        del e['timeInterval']
        del e['description']
        del e['customFieldValues']
        del e['userId']
        del e['billable']
        del e['taskId']
        del e['workspaceId']
        del e['isLocked']

    for e in entries:
        for entry_tag in e['tagIds']:
            for t in tags:
                if t['tag_id'] == entry_tag:
                    e['tags'].append(t['tag_name'])
    for e in entries:
        del e['tagIds']

    print('Entries received\n')
    return entries

# Start here


tags = GetTags()
projects = GetProjects()
entries = GetEntries()

# join entries and projects
df_e1 = pd.DataFrame(entries).set_index('projectId')
df_projects = pd.DataFrame(projects).set_index('project_id')
df_entries = df_e1.merge(df_projects, left_index=True, right_index=True)
df_entries.set_index(['entry_start', 'entry_finish'], inplace=True, drop=True)

# count new entries
new_entries = df_entries['entry_id'].count()

# connect to mongodb, and count saved entries
print('Checking mongodb\n')
client = pymongo.MongoClient(mongo_conn_string)
db = client['jim_blog']
clockify = db["clockify"]
saved_entries = db.clockify.count_documents({})

# if count in db is less, delete all and upload
if new_entries > saved_entries:
    d_count = clockify.delete_many({})
    print(d_count.deleted_count, " clockify documents deleted.")

    data_dict = df_entries.to_dict("records")
    clockify.insert_many(data_dict)
    print(db.clockify.count_documents({}), " clockify documents created")

else:
    print('nothing to do')
