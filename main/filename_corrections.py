'''this file contains code
on how I corrected filename prefixes 
for each projects'''

'''
while extending dataset for an existing project,
we assume the correction rules should apply to 
new files found (count of new files should be small)
For new project, we manually build this rules by exploration
and by means achieve 100% accuracy.
'''

import common, sql 
import sys, logging


def get_all_files(projectId):
    q='select * from file where project_id=%s'
    return sql.execute(q,(projectId,))

def get_base_names(files):
    'look at base names when exploring a new project'
    bases=[]
    for file in files:
        fullname=file['filepath_on_coverity']
        temp=fullname.split('/')
        if temp[1] not in bases:
            bases.append(temp[1])
    return bases

temp=[]
a=[]
hm={'Samba':['/samba','/bin/default','/base/src'],
    'Kodi':['/home/jenkins/workspace/LINUX-64-soverityscan_sandbox'],
    'Linux':['/linux'],
    'Firefox':['/mozilla','/base/src/mozilla']
    }

def startswithAny(s, checks):
    for check in checks:
        if s.startswith(check):
            return check
    return False

def correction(project,files):
    if project not in hm:
        return 0
    checks=hm[project]
    correctedCount=0
    for item in files:
        filename=item['filepath_on_coverity']
        cut = startswithAny(filename, checks)
        if cut:
            corrected=filename[len(cut):]
            fileId=item['id']
            q='update file set filepath_on_coverity=%s where id=%s'
            sql.execute(q,(corrected,fileId))
            correctedCount+=1
    return correctedCount


def remove_duplicates(projectId):
    q='''select filepath_on_coverity, count(*) as c
            from file
            where project_id = %s
            group by filepath_on_coverity
            having count(*) > 1'''
    results=sql.execute(q,(projectId,))

    logging.info("%s files have duplicates",len(results))

    for item in results:
        filepath=item['filepath_on_coverity']
        q='''select id from file
            where filepath_on_coverity=%s
            order by id asc '''
        temp=sql.execute(q,(filepath,))
        ids=[t['id'] for t in temp]
        
        max=-1
        main_id=-1
        for id in ids:
            q='select count(*) as c from filecommit where file_id=%s'
            c=sql.execute(q,(id,))[0]['c']
            if c>max:
                max=c
                main_id=id
        
        
        ids.remove(main_id)

        for replace_id in ids:
            #update alerts
            q='update alert set file_id=%s where file_id=%s'
            sql.execute(q,(main_id, replace_id))

            # #update occurrences
            # query="update occurrence set file_id="+str(main_id)+" where file_id="+str(replace_id)
            # execute(query)

            #delete from files
            q='delete from file where id=%s'
            sql.execute(q,(replace_id,))
        
def resolve_duplicates(projectId):
    files=get_all_files(projectId)

    q='select name from project where id=%s'
    project=sql.execute(q,(projectId,))[0]['name']

    correctedCount= correction(project,files)
    logging.info("%s files names have been corrected",correctedCount)

    remove_duplicates(projectId)

if __name__=='__main__':
    #read the project name
    project=sys.argv[1]
    projectId=common.get_project_id(project)

    resolve_duplicates(projectId)

