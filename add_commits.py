import pymysql
import sys
import datetime
import re
import os
import subprocess
import re
import shlex
import dateutil.parser as dp




connection = pymysql.connect(host='localhost',
                             user='root',
                             db='coverityscan',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)

#for each project - project name passed as an argument to the script
# for each file in files - doing the most outer loop
# get all the commits within desired timeframe (or,all?) - doing for all
# for all the file and commit pair put a new entry in filecommits - done
# look if the commit hash (or, id) already exists in commits table - done
# if not, make a new entry with all the required info - done
# for each filecommits (file and commit pair)
# look for that files modification in that commit diffs
# and parse that info to insert into diffs table 

def is_number(n):
    try:
        int(n)
    except ValueError:
        return False
    return True

def project_exists(project):
    query="select * from projects where name='"+project +"';"
    with connection.cursor() as cursor:
        cursor.execute(query)
        result=cursor.fetchall()
        if len(result)==1:
            return True
        elif len(result)==0:
            print ("project does not exist in database")
        else:
            print("more than one project found. fatal bug")
    return False

def get_all_files(project):
# and 
#                 f.idfiles not in (
#                     select distinct file_id from filecommits
#                 )
    with connection.cursor() as cursor:
        query='''select distinct f.idfiles, f.filepath_on_coverity
                from alerts a
                join files f
                on a.file_id=f.idfiles
                where a.stream="''' + str(project) + \
                '''" and a.is_invalid=0 and a.status='Fixed'
                and f.idfiles > ''' + str(start)+ \
                " and f.idfiles <= "+str(end)
        if project=='Firefox':
            query+= ''' and not (f.filepath_on_coverity  like '/obj-x86_64-unknown-linux-gnu%'
                        or f.filepath_on_coverity  like '/obj-coverity%'
                        or f.filepath_on_coverity  like '/obj-x86_64-pc-linux-gnu%'
                        or f.filepath_on_coverity  like '/usr%')'''
                    #embedding, rdf, 
        #query="select * from files where project='"+str(project)+"' and idfiles >" + str(last_checked)+";"
        cursor.execute(query)
        results=cursor.fetchall()
        return results

def commitId_ifExists(sha):
    with connection.cursor() as cursor:
        query="select idcommits from commits where project='"+str(project)+"' and sha='"+str(sha)+"';"
        cursor.execute(query)
        result=cursor.fetchone()
        if result and 'idcommits' in result.keys():
            return result['idcommits']
        return None

def add_commit(commit):
    arguments=[]
    
    arguments.append(commit["hash"])
    arguments.append(commit["author"])
    arguments.append(commit["author_email"])
    arguments.append(commit["author_date"].strftime("%Y-%m-%d %H:%M:%S"))
    arguments.append(commit["committer"])
    arguments.append(commit["committer_email"])
    arguments.append(commit["commit_date"].strftime("%Y-%m-%d %H:%M:%S"))
    arguments.append(commit["message"])
    
    #giving null to full commit data
    affected_files='null'
    lines_added='null'
    lines_removed='null'
    
    arguments.append(affected_files)
    arguments.append(lines_added)
    arguments.append(lines_removed)

    if 'merge' in commit.keys():
        arguments.append('True')
    else:
       arguments.append('False') 

    arguments.append(project)
    
    # add an escaping string function. not the best practice. but easiest fix.
    for a in arguments:
        if type(a)==str:
            a=connection.escape_string(a)
            a=a.replace('\\','')

    query="insert into commits values (null,"
    for idx, arg in enumerate(arguments):
        #value cleaning
        arg=str(arg) #if not string
        arg=arg.strip() #if any whitespace ahead or trailing
        #remove illegal character
        arg=arg.replace('"',"'")

        if is_number(arg) or arg=="null":
            query+=arg
        else:
            query+='"'+arg+'"'
        if idx<len(arguments)-1:
            query+=","
    query+=");"
    with connection.cursor() as cursor:
        try:
            query=query.replace("\\","")
            cursor.execute(query)
        except Exception as e:
            print(e,query)

def filecommitId_ifExists(file_id,commit_id):
    if file_id==None:
        file_id=-1
    if commit_id==None:
        commit_id=-1
    with connection.cursor() as cursor:
        query="select idfilecommits from filecommits where file_id="+str(file_id)+" and commit_id="+str(commit_id)+";"
        cursor.execute(query)
        result=cursor.fetchone()
        if result and 'idfilecommits' in result.keys():
            return result['idfilecommits']
        return None
def add_filecommits(file_id,filepath,commit_id,commit):
    arguments=[]
    arguments.append(str(file_id))
    arguments.append(str(commit_id))
    arguments.append(commit['change_type'])
    arguments.append(commit['lines_added'])
    arguments.append(commit['lines_removed'])
    
    # add an escaping string function. not the best practice. but easiest fix.
    for a in arguments:
        if type(a)==str:
            a=connection.escape_string(a)

    query="insert into filecommits values (null,"
    for idx, arg in enumerate(arguments):
        #value cleaning
        arg=str(arg) #if not string
        arg=arg.strip() #if any whitespace ahead or trailing
        #remove illegal character
        arg=arg.replace('"',"'")

        if is_number(arg) or arg=="null":
            query+=arg
        else:
            query+='"'+arg+'"'
        if idx<len(arguments)-1:
            query+=","
    query+=");"
    with connection.cursor() as cursor:
        try:
            # print(query)
            cursor.execute(query)
        except Exception as e:
            print(e,query)

def parse_diff(diff,filecommit_id):
    #can throw exception? 
    # #handle them
    results=[]
    diff=diff.strip()

    #what if there is more than 2 @? replace that with blanks
    diff=re.sub('[@]{3,}','',diff)

    diffs=diff.split("@@")
    diffs=diffs[1:]
    if len(diffs)%2!=0:
        raise Exception("logic error")
    i=0
    while i<len(diffs):
        temp=diffs[i]
        temp=temp.strip()
        temp=temp.split(" ")
        if len(temp)!=2:
            #don't know if it is only old and new
            #skip this one
            i+=2
            continue
        old=temp[0]
        new=temp[1]
        old=old.split(",")
        if len(old)==2:
            old_start_line=old[0]
            old_count=old[1]
        else:
            old_start_line='null'
            old_count='null'
        new=new.split(",")
        if len(new)==2:
            new_start_line=new[0]
            new_count=new[1]
        else:
            new_start_line='null'
            new_count='null'
        content=connection.escape_string(diffs[i+1])
        temp=[filecommit_id,old_start_line,old_count,new_start_line,new_count,content]
        results.append(temp)
        i+=2
    return results

def get_start_end_date():
    d={}
    with connection.cursor() as cursor:
        query="select start_date, end_date from projects where name='" + project + "';"
        cursor.execute(query)
        result=cursor.fetchone()
        start=result['start_date']
        end=result['end_date']
        start=start.strftime('%Y-%m-%d')
        d['start_date']=start
        end=end.strftime('%Y-%m-%d')
        d['end_date']=end
        return d
def mine_gitlog(filepath):
    temp=get_start_end_date()
    start_date=temp['start_date']
    end_date= temp['end_date']
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
        print(e,"file does not exist?")
        return []
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
    return commits



def add_diff(commit,filepath,filecommit_id):
    filepath=filepath.split("/")
    filename=filepath[-1]
    for m in commit.modifications:
        if m.filename==filename:
            try:
                results=parse_diff(m.diff,filecommit_id)
            except Exception as e:
                print(e)
                continue
            for arguments in results:
                # add an escaping string function. not the best practice. but easiest fix.
                for a in arguments:
                    if type(a)==str:
                        a=connection.escape_string(a)
                        
                query="insert into diffs values (null,"
                for idx, arg in enumerate(arguments):
                    #value cleaning
                    arg=str(arg) #if not string
                    arg=arg.strip() #if any whitespace ahead or trailing
                    #remove illegal character
                    arg=arg.replace('"',"'")

                    if is_number(arg) or arg=="null":
                        query+=arg
                    else:
                        query+='"'+arg+'"'
                    if idx<len(arguments)-1:
                        query+=","
                query+=");"
                with connection.cursor() as cursor:
                    try:
                        cursor.execute(query)
                    except Exception as e:
                        print(e,query)

def diffId_ifExists(filecommit_id):
    if filecommit_id==None:
        filecommit_id=-1
    with connection.cursor() as cursor:
        query="select iddiffs from diffs where filecommit_id="+str(filecommit_id)+";"
        cursor.execute(query)
        result=cursor.fetchone()
        if result and 'iddiffs' in result.keys():
            return result['iddiffs']
        return None


                  
''' add commit data for each affected file within start and end date'''
if __name__=="__main__":
    #read command line arguments
    project=sys.argv[1]
    path="/Users/nasifimtiaz/Desktop/new_data/"+sys.argv[2]
    start=sys.argv[3]
    end=sys.argv[4]
    os.chdir(path)
    
    #check if project exists
    if not project_exists(project):
        print("project does not exist")
        exit()

    # get all the files from database
    files=get_all_files(project)

    print(len(files),files[0],files[-1])
    for f in files:
        #get fid and see if it is already covered

        #parse local filepath
        path=f["filepath_on_coverity"]
        path=path[1:] #cut the beginning slash
        print(path)
        commits=mine_gitlog(path)
        print(len(commits))
        for commit in commits:
            sha=commit["hash"]
            if commitId_ifExists(sha)==None:
                add_commit(commit) #not adding affected files count, lines added, and removed for now
            commit_id=commitId_ifExists(sha)   
            file_id=f["idfiles"]
            if filecommitId_ifExists(file_id,commit_id)==None:
                add_filecommits(file_id,path,commit_id,commit)
            filecommit_id = filecommitId_ifExists(file_id,commit_id)
        print(f['idfiles'])
            #adding no diff
       
        
    print(datetime.datetime.now())       


            
            



