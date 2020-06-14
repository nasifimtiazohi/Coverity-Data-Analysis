'''for selected files,
add detailed commit history of that file
alingside code diff information'''
import common, sql
import sys
import datetime
import re
import os
import subprocess
import re
import shlex
import dateutil.parser as dp
import logging

'''
for each project - project name passed as an argument to the script
for each file in files - doing the most outer loop
get all the commits within desired timeframe (or,all?) - doing for all
for all the file and commit pair put a new entry in filecommits - done
look if the commit hash (or, id) already exists in commits table - done
if not, make a new entry with all the required info - done
for each filecommits (file and commit pair)
TODO:look for that files modification in that commit diffs
TODO: and parse that info to insert into diffs table 
'''

def get_all_files(projectId, start=None, end=None):
    '''
    return the list of all yet unprocessed files for fixed valid alerts

    Parameters
    -----------
    projectId
    start and end can be passed to select a range of search space for file id

    Return
    -------
    List of {Id , filepath}
    '''

    query = '''select distinct f.id, f.filepath_on_coverity
            from alert a
            join file f
            on a.file_id=f.id
            where f.project_id=%s
            and a.is_invalid=0
            and a.status='Fixed' '''
    if start:
        query+= ' where id >= %s '
    if end:
        query+= ' where id <= %s'
    

    if projectId== 3: #for firefox
        query+= ''' and not (f.filepath_on_coverity  like '/obj-x86_64-unknown-linux-gnu%'
                    or f.filepath_on_coverity  like '/obj-coverity%'
                    or f.filepath_on_coverity  like '/obj-x86_64-pc-linux-gnu%'
                    or f.filepath_on_coverity  like '/usr%')'''
                #embedding, rdf, 
    
    if not start and not end:
        results = sql.execute(query,(projectId,))
    elif start and end:
        results = sql.execute(query,(projectId,start,end))
    elif start:
        results = sql.execute(query,(projectId,start))
    elif end:
        results = sql.execute(query,(projectId,end))
    
    return results

def commitId_exists(projectId, sha):
    q='select id from commit where project_id=%s and sha=%s'
    results=sql.execute(q,(projectId,sha))
    if results:
        return results[0]['id']
    return None

def add_commit(commit, projectId):
    arguments=[
        None, projectId,
        commit["hash"],commit["author"],commit["author_email"],
        commit["author_date"].strftime("%Y-%m-%d %H:%M:%S"),
        commit["committer"], commit["committer_email"],
        commit["commit_date"].strftime("%Y-%m-%d %H:%M:%S"), commit["message"]
    ]
    #giving null to full commit data
    #NOT PARSING FULL COMMIT DATA AS NOT RELEVANT TO THIS PROJECT
    affected_files= lines_added = lines_removed = None
    arguments += [affected_files,lines_added,lines_removed]
    if 'merge' in commit.keys():
        arguments.append('True')
    else:
       arguments.append('False') 
    
    q='insert into commit values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'
    sql.execute(q,tuple(arguments))

def filecommitId_exists(file_id,commit_id):
    if not file_id or not commit_id:
        logging.error("look in filecommitId_ifExists method")
        return 
    q='select id from filecommit where file_id=%s and commit_id=%s'
    results=sql.execute(q,(file_id,commit_id))
    if results:
        return results[0]['id']
    return None


    with connection.cursor() as cursor:
        query="select idfilecommits from filecommits where file_id="+str(file_id)+" and commit_id="+str(commit_id)+";"
        cursor.execute(query)
        result=cursor.fetchone()
        if result and 'idfilecommits' in result.keys():
            return result['idfilecommits']
        return None

def add_filecommits(file_id, commit_id, commit):
    arguments=[
        None, file_id, commit_id,
        commit['change_type'],commit['lines_added'],commit['lines_removed']
    ]
    q='insert into filecommit values(%s,%s,%s,%s,%s,%s)'
    sql.execute(q,tuple(arguments))

def mine_gitlog(fileId, filepath):
    def set_start_end_date():
         #determine start and end date range to search commit within
        temp=common.get_start_end_date()
        start_date=temp['start_date']
        end_date= temp['end_date']
        ## overwrite start date if there is already any filecommit present in the database
        ## (which means the file was analyzed at least upto that point before)
        q='''select max(commit_date) as lastdate from filecommit fc
            join commit c on fc.commit_id = c.id
            where file_id=%s  '''
        results=sql.execute(q,(fileId,))
        if results:
            start_date=results[0]['lastdate']
    start_date, end_date = set_start_end_date()

    try:
        lines = subprocess.check_output(
            shlex.split('git log --follow --pretty=fuller --stat \
            --after="'+start_date+ 
            ' 00:00" --before="'+end_date+' 23:59"  \
            -- '+filepath), 
            stderr=subprocess.STDOUT,
            encoding="437"
            ).split('\n')
    except Exception as e:
        logging.info("no commits found withn {} and %s ", e)

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
    if commit:   
        commits.append(commit) 
    return commits


                  

if __name__=="__main__":
    ''' add commit data for each affected file within start and end date'''
    # TODO: make paralellize and run for all projects at once

    #read command line arguments
    #TODO: might just make it over all projects when paralellized
    project=sys.argv[1]
    projectId=common.get_project_id()
    path="/Users/nasifimtiaz/Desktop/repos_coverity"+common.get_repo_name(projectId)
    os.chdir(path)
    # start=sys.argv[3]
    # end=sys.argv[4]
    

    # get all the files from database
    files=get_all_files(project)

    print(len(files),files[0],files[-1])

    for f in files:
        #get fid and see if it is already covered
        file_id=f["id"]
        #parse local filepath
        path=f["filepath_on_coverity"]
        path=path[1:] #cut the beginning slash
        print(path)

        commits=mine_gitlog(path)
        print(len(commits))

        for commit in commits:
            sha=commit["hash"]
            if not commitId_exists(projectId, sha):
                #not adding affected files count, lines added, and removed for now in this script
                add_commit(commit, projectId) 
            commit_id=commitId_exists(projectId, sha)   
            
            if not filecommitId_exists(file_id,commit_id):
                add_filecommits(file_id,commit_id,commit)
            filecommit_id = filecommitId_exists(file_id,commit_id)
        #adding no diff
             


            
            



