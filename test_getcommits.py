import argparse
import os
import subprocess
import re
import datetime
import shlex
#import git
path="/Users/nasifimtiaz/Desktop/new_data/gecko-dev"
leading_4_spaces = re.compile('^    ')
# # #dom/base/Element.cpp
os.chdir(path)
import dateutil.parser as dp

def get_filecommits(filepath):
    lines = subprocess.check_output(
            ['git', 'log','--follow','--pretty=fuller','--stat',filepath], stderr=subprocess.STDOUT
        ).split('\n')
    print(len(lines))
    commits=[]
    commit={}
    for nextLine in lines: 
        if nextLine == '' or nextLine == '\n':
            # ignore empty lines
            pass
        elif bool(re.match('commit ', nextLine)):
            # commit xxxx
            if len(commit) != 0:		## new commit, so re-initialize
                commits.append(commit)
                commit = {}
            commit = {'hash' : re.match('commit (.*)', nextLine, re.IGNORECASE).group(1) }
        elif bool(re.match('merge:', nextLine, re.IGNORECASE)):
            # Merge: xxxx xxxx
            pass
        elif bool(re.match('Author:', nextLine,)):
            # Author: xxxx <xxxx@xxxx.com>
            m = re.compile('Author:([ ]+)(.*) <(.*)>').match(nextLine)
            commit['author'] = m.group(2)
            commit['author_email'] = m.group(3)
        elif bool(re.match('AuthorDate:', nextLine, re.IGNORECASE)):
            # Date: xxx
            fulldate=re.match("AuthorDate:([ ]+)(.*)",nextLine).group(2)
            commit['author_date']=dp.parse(fulldate)
        elif bool(re.match('Commit:', nextLine)):
            # Commit: xxxx <xxxx@xxxx.com>
            m = re.compile('Commit:([ ]+)(.*) <(.*)>').match(nextLine)
            commit['committer'] = m.group(2)
            commit['committer_email'] = m.group(3)
        elif bool(re.match('CommitDate:', nextLine, re.IGNORECASE)):
            # Date: xxx
            fulldate=re.match(
                "CommitDate:([ ]+)(.*)",nextLine).group(2)
            commit['commit_date']=dp.parse(fulldate)
        elif bool(re.match('    ', nextLine, re.IGNORECASE)):
            # (4 empty spaces)
            if 'message' not in commit.keys():
                commit['message'] = nextLine.strip()
            else:
                commit['message']+='\n'+nextLine
        #handle change type  
        #commit['change_type']           
        elif "file changed" in nextLine:
            info=nextLine.split(',')
            if len(info)==3:
                commit['change_type']='ModificationType.MODIFY'
                if '+' in info[1]:
                    add=info[1].strip()
                    add=add.split(' ')
                    commit['lines_added']=int(add[0])
                if '-' in info[2]:
                    rem=info[2].strip()
                    rem=rem.split(' ')
                    commit['lines_removed']=int(rem[0])
            else:
                if '+' in info[1]:
                    commit['change_type']='ModificationType.ADD'
                    add=info[1].strip()
                    add=add.split(' ')
                    commit['lines_added']=int(add[0])
                elif '-' in info[1]:
                    commit['change_type']='ModificationType.DELETE'
                    rem=info[1].strip()
                    rem=rem.split(' ')
                    commit['lines_removed']=int(rem[0])
        

    commits.append(commit) 
    print(commits[-1])
    print(commits[-2])
    return commits

    

def test():
    print("what")
    lines = subprocess.check_output(
            ['git', 'log','--follow','--stat','dom/media/MediaDecoderStateMachine.cpp'], stderr=subprocess.STDOUT
        )
    os.chdir("/Users/nasifimtiaz/Desktop/890_Written_Prelim")
    temp=open("temp.txt","w")
    temp.write(lines)
    temp.close()

test()
    
    

