### pymydriller only works with python3
import pymysql
import pydriller
import sys
import datetime

#read command line arguments
project=sys.argv[1]
path="/Users/nasifimtiaz/Desktop/new_data/"+sys.argv[2]



connection = pymysql.connect(host='localhost',
                             user='root',
                             db='890coverity',
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
    query="select * from projects where project='"+project +"';"
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
    with connection.cursor() as cursor:
        query="select * from files where project='"+str(project)+"';"
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
    print("what happened")
    arguments=[]
    arguments.append(commit.hash)
    arguments.append(commit.author.name)
    arguments.append(commit.author.email)
    arguments.append(commit.author_date.strftime("%Y-%m-%d %H:%M:%S"))
    arguments.append(commit.committer.name)
    arguments.append(commit.committer.email)
    arguments.append(commit.committer_date.strftime("%Y-%m-%d %H:%M:%S"))
    arguments.append(commit.msg)
    arguments.append(project)
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
            cursor.execute(query)
            print(query)
        except Exception as e:
            print(e,query)

def filecommitId_ifExists(file_id,commit_id):
    with connection.cursor() as cursor:
        query="select idfilecommits from filecommits where file_id="+str(file_id)+" and commit_id="+str(commit_id)+";"
        cursor.execute(query)
        result=cursor.fetchone()
        if result and 'idfilecommits' in result.keys():
            return result['idfilecommits']
        return None
def add_filecommits(file_id,commit_id):
    with connection.cursor() as cursor:
        query="insert into filecommits values(null,"+str(file_id)+","+str(commit_id)+");"
        try:
            cursor.execute(query)
            print(query)
        except Exception as e:
            print(e,query)

def parse_diff(diff,filecommit_id):
    results=[]
    diff=diff.strip()
    diffs=diff.split("@@")
    diffs=diffs[1:]
    print(diffs)
    if len(diffs)%2!=0:
        print("logic error")
    i=0
    while i<len(diffs):
        temp=diffs[i]
        temp=temp.strip()
        temp=temp.split(" ")
        old=temp[0]
        new=temp[1]
        old=old.split(",")
        old_start_line=old[0]
        old_count=old[1]
        new=new.split(",")
        new_start_line=new[0]
        new_count=new[1]
        content=diffs[i+1]
        temp=[filecommit_id,old_start_line,old_count,new_start_line,new_count,content]
        results.append(temp)
        i+=2
    return results




def add_diff(commit,filepath,filecommit_id):
    filepath=filepath.split("/")
    filename=filepath[-1]
    for m in commit.modifications:
        if m.filename==filename:
            results=parse_diff(m.diff,filecommit_id)
            for arguments in results:
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
                        print(query)
                    except Exception as e:
                        print(e,query)

def diffId_ifExists(filecommit_id):
   with connection.cursor() as cursor:
        query="select iddiffs from diffs where filecommit_id="+str(filecommit_id)+";"
        cursor.execute(query)
        result=cursor.fetchone()
        if result and 'iddiffs' in result.keys():
            return result['iddiffs']
        return None


if __name__=="__main__":
    
    #check if project exists
    if not project_exists(project):
        print("project does not exist")
        exit()
    
    #initiate repo
    repo=pydriller.RepositoryMining(path)

    # get all the files from database
    files=get_all_files(project)

    for f in files:
        #parse local filepath
        path=f["filepath_on_coverity"]
        path=path[1:] #cut the beginning slash
        repo._filepath=path
        print(path)
        for commit in repo.traverse_commits():
            #check if the commit is already in the database through hash
            sha=commit.hash
            if commitId_ifExists(sha)==None:
                add_commit(commit)
            commit_id=commitId_ifExists(sha)

            #add file and commit pair
            file_id=f["idfiles"]
            if filecommitId_ifExists(file_id,commit_id)==None:
                print(file_id,commit_id)
                add_filecommits(file_id,commit_id)
            filecommit_id = filecommitId_ifExists(file_id,commit_id)

            print(filecommit_id)

            #look for diff
            if diffId_ifExists(filecommit_id)==None and filecommit_id:
                add_diff(commit,path,filecommit_id)


            
            



