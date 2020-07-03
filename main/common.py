import sys
import sql
import os
import numpy as np
import pandas as pd
import coloredlogs, logging
coloredlogs.install()

def is_integer(n):
    try:
        int(n)
    except ValueError:
        return False
    return True

def read_xml_file_to_list_of_dicts(file):
    import xml.etree.ElementTree as ET
    try:
        tree = ET.parse(file)
        root = tree.getroot()
    except:
        return [] #no xml data

    datalist=[]
    for child in root:
        data=child.attrib
        datalist.append(data)
    
    return datalist

def get_project_id(project):
    q='select id from project where name=%s'
    results=sql.execute(q,(project,))
    if not results:
        return None
    elif len(results) >1 :
        logging.error("more than one project with the name %s",project)
    return results[0]['id']

def replace_blankString_with_NaN(df):
    return df.replace(r'^\s*$', np.NaN, regex=True)


def get_start_end_date(projectId, connection = None):
    '''returns as dateformat '''
    d={}

    q="select start_date, end_date from project where id=%s"
    results=sql.execute(q,(projectId,),connection=connection)
    if not results:
        return d
    result=results[0]

    start=result['start_date']
    end=result['end_date']

    return start, end

def get_repo_name(projectId, connection = None):
    q='select github_url from project where id=%s'
    results=sql.execute(q,(projectId,), connection=connection)
    gh_url =  results[0]['github_url']
    #take the last part
    return gh_url.split('/')[-1]


def get_snapshot_date(projectId, snapshotId, connection=None):
    q='''select * from snapshot
        where project_id=%s
        and id=%s; '''
    results=sql.execute(q,(projectId, snapshotId), connection=connection )
    if results:
        temp=results[0]
        if temp['code_version_date']:
            last_detected_date=temp['code_version_date']
        else:
            last_detected_date=temp["date"]
        return last_detected_date
    else:
        logging.error('invalid arguments while finding snapshot date')

def get_next_snapshotId(projectId, snapshotId, connection = None):
    q='''select id from snapshot
        where project_id=%s
        and last_snapshot=%s'''
    results=sql.execute(q,(projectId, snapshotId), connection=connection)
    if results:
        try:
            return results[0]['id']
        except Exception as e:
            raise Exception(e,snapshotId,projectId, results)
    else:
        raise Exception(e,snapshotId,projectId)
        logging.error('invalid arguments while finding snapshot date',snapshotId)


def get_snapshot_count(projectId):
    q='select count(*) as c from snapshot where project_id=%s'
    return sql.execute(q,(projectId,))[0]['c']

def get_alert_count(projectId):
    q='select count(*) as c from alert where project_id=%s'
    return sql.execute(q,(projectId,))[0]['c']

def switch_dir_to_project_path(projectId, connection=None):
    path="/Users/nasifimtiaz/Desktop/repos_coverity/" + get_repo_name(projectId, connection=connection)
    os.chdir(path)

def get_file_id(filename, projectId,connection=None):
    selectQ='select id from file where filepath_on_coverity =%s and project_id=%s '
    results=sql.execute(selectQ,(filename, projectId), connection=connection)
    if not results:
        #check if filename startswith /
        if not filename.startswith('/'):
            filename = '/'+ filename
        insertQ='insert into file values(null,%s,%s,null)'
        sql.execute(insertQ,(projectId, filename), connection=connection)
        results=sql.execute(selectQ,(filename, projectId), connection=connection)
    return results[0]['id']


if __name__=='__main__':
    a =get_snapshot_date(2,10922) 
    print(type(a))
    




 