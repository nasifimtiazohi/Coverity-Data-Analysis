import sys
sys.path.append('../../main')
import common, sql
import re
import logging
import os
import shlex
import subprocess
import dateutil.parser as dp
from multiprocessing import Pool
import datetime
from itertools import groupby
import csv

def get_file_function_names(projectId,commits):
    common.switch_dir_to_project_path(projectId)
    allFiles=[]
    hm = {}
    for sha in commits:
        lines = subprocess.check_output(
            shlex.split("git show --name-only "+sha),
            stderr=subprocess.STDOUT, encoding="437").split('\n')
        split_at=''
        files=[list(g) for k, g in groupby(lines, lambda x: x != split_at) if k][-1]
        allFiles += files
        for file in files:
            functions = get_function_names(file,sha)
            if file in hm:
                hm[file]+= functions
            else:
                hm[file]=functions
    allFiles=list(set(allFiles))
    
    for k in hm.keys():
        hm[k]=list(set(hm[k]))
        
    return allFiles, hm

def processHeader(line):
    if not line:
        return 'null'
    line=line.strip()
    if '(' not in line:
        return None 
    idx=line.find('(')
    line=line[:idx]
    line=line.strip()
    line=line.split(' ')[-1]
    
    #scoping
    if '::' in line:
        line=line.split('::')[-1]
    
    return line
    
def get_function_names(file, sha):
    functions=[]  
    diff = subprocess.check_output(
        shlex.split("git show "+sha+" -- "+file),
        stderr=subprocess.STDOUT, encoding="437")
    diff = re.sub('[@]{3,}', '', diff)
    parts = diff.split('@@')
    del parts[0]  # initial texts
    ind=1
    while ind < len(parts):
        cur_diff = parts[ind]
        line = cur_diff.split('\n')[0]
        functions.append(processHeader(line))
        ind += 2
    return functions

def get_alert_on_files(publishDate,files):
    files=['/'+f for f in files]
    results=[]
    for file in files:
        q='''select * from alert a
            join memory_error me on a.alert_type_id = me.alert_type_id
            join file f on a.file_id = f.id
            where memory=1
            and filepath_on_coverity = %s
            and first_detected < %s'''
        results += sql.execute(q,(file,publishDate))
    return results
 
def get_alert_on_functions(publishDate, file, func):
    functionAlerts=[]
    if func is None:
        return functionAlerts
    elif func=='null':
        q='''select * from alert a
        join memory_error me on a.alert_type_id = me.alert_type_id
        join file f on a.file_id = f.id
        where memory=1
        and filepath_on_coverity = %s
        and `function` is null
        and first_detected < %s'''
        results=sql.execute(q,('/'+file,publishDate))
    else:
        q='''select * from alert a
            join memory_error me on a.alert_type_id = me.alert_type_id
            join file f on a.file_id = f.id
            where memory=1
            and filepath_on_coverity = %s
            and `function` = %s
            and first_detected < %s'''
        results=sql.execute(q,('/'+file,func,publishDate))
    if results:
        functionAlerts += results 
    return functionAlerts 
            
    
if __name__=='__main__':
    with open('linuxmemoryexploit.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        projectId=None
        for row in csv_reader:
            if line_count == 0:
                print(f'Column names are {", ".join(row)}')
                line_count += 1
            else:
                if not projectId:
                    projectId=7
                commits=row[-1].replace(' ','').split(',')
                cve=row[0]
                try:
                    q='select publish_date from cve where id = %s'
                    publishDate=sql.execute(q,(cve))[0]['publish_date']
                    files, functions = get_file_function_names(projectId, commits)
                    fileAlerts= get_alert_on_files(publishDate, files)
                    unparseable = 0
                    for file in functions.keys():
                        unparseable+= functions[file].count(None)
                    functionAlerts= []
                    for file in functions.keys():
                        for func in functions[file]:
                                functionAlerts += get_alert_on_functions(publishDate, file, func)
                    t=[cve, len(fileAlerts), unparseable, len(functionAlerts)]
                    print(','.join(str(x) for x in t))
                except:
                    continue
                
                     
                    
                
                    
                        
                
                
                
        print(f'Processed {line_count} lines.')