import argparse
import os
import subprocess
import re
import datetime
import shlex

leading_4_spaces = re.compile('^    ')
#dom/base/Element.cpp
os.chdir("/Users/nasifimtiaz/Desktop/new_data/gecko-dev")
print(datetime.datetime.now())
lines = subprocess.check_output(
        ['git', 'log','--follow',"--pretty='%an'","dom/html/nsHTMLContentSink.cpp"], stderr=subprocess.STDOUT
    ).split('\n')
print(len(lines))
#print(lines)
print(datetime.datetime.now())

def get_commits():
    lines = subprocess.check_output(
        ['git', 'log','--follow',"--pretty='%an'","dom/base/Element.cpp"], stderr=subprocess.STDOUT
    ).split('\n')
    print(len(lines))
    
    # commits = []
    # current_commit = {}

    # def save_current_commit():
    #     title = current_commit['message'][0]
    #     message = current_commit['message'][1:]
    #     if message and message[0] == '':
    #         del message[0]
    #     current_commit['title'] = title
    #     current_commit['message'] = '\n'.join(message)
    #     commits.append(current_commit)

    # for line in lines:
    #     if not line.startswith(' '):
    #         if line.startswith('commit '):
    #             if current_commit:
    #                 save_current_commit()
    #                 current_commit = {}
    #             current_commit['hash'] = line.split('commit ')[1]
    #         else:
    #             try:
    #                 key, value = line.split(':', 1)
    #                 current_commit[key.lower()] = value.strip()
    #             except ValueError:
    #                 pass
    #     else:
    #         current_commit.setdefault(
    #             'message', []
    #         ).append(leading_4_spaces.sub('', line))
    # if current_commit:
    #     save_current_commit()
    # return commits