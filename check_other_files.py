'''after searching for file commits within start and end date range,
look for other files if they have any commit ever in history,
as prior check could miss some due to date range.
If yes, put one in file commit.
If no, then files that have no commits in filecommits,
we will know that they are non-project files'''
import pymysql
import sys
import datetime
import re
import os
import subprocess
import re
import shlex
import dateutil.parser as dp
import add_commits as ac


#read command line arguments
project=sys.argv[1]
path="/Users/nasifimtiaz/Desktop/new_data/"+sys.argv[2]
os.chdir(path)

ac.project=project


connection = pymysql.connect(host='localhost',
                             user='root',
                             db='soverityscan_sandbox',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)


def execute(query):
    with connection.cursor() as cursor:
        cursor.execute(query)
        results=cursor.fetchall()
    return results

query='''select distinct f.idfiles, f.filepath_on_coverity
                from alerts a
                join files f
                on a.file_id=f.idfiles
                where a.stream="'''+project+'''"
                and a.is_invalid=0
                and f.idfiles not in (
                   select distinct file_id from filecommits
            )'''
if project=='Firefox':
            query+= ''' and not (f.filepath_on_coverity  like '/obj-x86_64-unknown-linux-gnu%'
                        or f.filepath_on_coverity  like '/obj-coverity%'
                        or f.filepath_on_coverity  like '/obj-x86_64-pc-linux-gnu%'
                        or f.filepath_on_coverity  like '/usr%')'''
results=execute(query)
print(len(results))
for item in results:
    filepath=item['filepath_on_coverity'][1:]
    print(filepath)
    lines = subprocess.check_output(
            shlex.split('git log --follow --pretty=fuller --stat -n 1 \
            -- '+filepath), 
            stderr=subprocess.STDOUT,
            encoding="437"
            ).split('\n')
    count=len(lines)-1
    if count==0:
        print("this is a other-file")
    else:
        print("this is not")
        commits=[]
        commit={}
        for idx, nextLine in enumerate(lines): 
            if nextLine == '' or nextLine == '\n':
                # ignore empty lines
                pass
            if bool(re.match('commit ', nextLine)):
                # commit xxxx
                ## new commit, so re-initialize
                if len(commit) != 0: ## bypasses the first time		
                    commits.append(commit) ## add previous commit to the list
                    commit = {}
                commit['hash'] = re.match('commit (.*)', nextLine, re.IGNORECASE).group(1) 
            elif bool(re.match('merge:', nextLine, re.IGNORECASE)):
                # Merge: xxxx xxxx
                # not extracting merge commit information
                commit['merge']= 'True'
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
                        commit['lines_removed']=0
                    elif '-' in info[1]:
                        commit['change_type']='ModificationType.DELETE'
                        rem=info[1].strip()
                        rem=rem.split(' ')
                        commit['lines_removed']=int(rem[0])
                        commit['lines_added']=0
                if lines[idx-1] and "=>" in lines[idx-1]:
                    #check if file renaming was done
                    commit['change_type']='ModificationType.RENAME'  
        if len(commit)!=0:   
            commits.append(commit) 
        for commit in commits:
            sha=commit["hash"]
            if ac.commitId_exists(sha)==None:
                ac.add_commit(commit) #not adding affected files count, lines added, and removed for now
            commit_id=ac.commitId_exists(sha)   
            file_id=item["idfiles"]
            if ac.filecommitId_exists(file_id,commit_id)==None:
                ac.add_filecommits(file_id,path,commit_id,commit)
            ac.filecommit_id = ac.filecommitId_exists(file_id,commit_id)
        print(item['idfiles'])