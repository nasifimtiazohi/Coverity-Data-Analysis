'''
redundant code for parsing diff
add_diff uses commit object from pydriller which is not used anymore in this project
however parse_diff should work on raw diff content
'''

import common, sql
import re
import logging

def parse_diff(diff,filecommit_id):
    # can throw exception TODO: handle them
    results=[]
    diff=diff.strip()

    # && is marked as different block of changes in git logs
    # what if there is more than 2 @? replace that with blanks
    diff=re.sub('[@]{3,}','',diff)

    diffs=diff.split("@@")
    diffs=diffs[1:]
    if len(diffs)%2!=0:
        #NOTE: changes are marked with @@ at start and end so guaranteed to have 2x length
        logging.error("diff length not 2x after @@ splitting")
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
            old_start_line=None
            old_count=None
        new=new.split(",")
        if len(new)==2:
            new_start_line=new[0]
            new_count=new[1]
        else:
            new_start_line=None
            new_count=None
        content=diffs[i+1]
        temp=[filecommit_id,old_start_line,old_count,new_start_line,new_count,content]
        
        #do string cleaning
        for i,arg in enumerate(temp):
            arg=str(arg) #if not string
            arg=arg.strip() #if any whitespace ahead or trailing
            if common.is_integer(arg):
                arg=int(arg)
            temp[i]=arg
        
        results.append(temp)
        i+=2
    return results

def add_diff(commit, file_id, filepath, filecommit_id):
    #NOTE: Commit is a PyDriller object
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
                arguments.insert(0,None)
                q='insert into diffs values(%s,%s,%s,%s,%s,%s,%s)'
                sql.execute(q,tuple(arguments))

def diffId_count(filecommit_id):
    if not filecommit_id:
        logging.error("check diffid_Exitsts")
        return
    q='select count(*) as c from diff where filecommit_id=%s'
    results=sql.execute(q,(filecommit_id,))
    return results[0]['c']