import common
import sql
import sys
import os
import subprocess
import shlex
import logging
import re


def get_alerts(projectId):
    '''get fixed alerts that haven't been analyzed for fix complexity yet'''
    q = '''select distinct ac.single_fix_commit, c.id as idcommits,
                f.id as idfiles, c.*,f.*,a.id as idalerts
            from actionability ac
            join alert a
            on ac.alert_id=a.id
            join commit c
            on c.id = ac.single_fix_commit
            join file f
            on f.id = a.file_id
            where ac.single_fix_commit is not null
            and ac.actionability=1
            and a.is_invalid=0
            and a.status='Fixed'
            and a.project_id =%s
            and a.id not in
            (select distinct alert_id from fix_complexity)'''
    return sql.execute(q, (projectId,))


def get_file_diffs(difflog):
    diffs = difflog.split('diff --git ')
    del diffs[0]  # initial texts
    return diffs


def remove_blank_lines_and_comments(diff):
    diff = re.sub('/\\*(.|\n)*\\*/', '', diff)  # remmoving multiline comments
    lines = diff.split('\n')
    copy = []
    for line in lines:
        line = re.sub('//(.*)', '', line)  # removing single line comments
        line = line.strip()  # stripping trailing whitespaces
        if not (line == '' or line == '\n'):
            # however changes will start with + or -
            if line.startswith('+') or line.startswith('-'):
                temp = line[1:]  # take the actual line
                temp = temp.strip()  # stripping trailing whitespaces
                if not (temp == '' or temp == '\n'):
                    copy.append(line)
            else:
                copy.append(line)
    return '\n'.join(copy)


def loc_and_logical_block_change(filediff):
    loc = 0
    logical = 0
    diff = filediff

    # removing any instance with more than two @@
    diff = re.sub('[@]{3,}', '', diff)
    parts = diff.split('@@')
    del parts[0]  # initial texts
    ind = 1
    while ind < len(parts):
        cur_diff = parts[ind]
        cur_diff = remove_blank_lines_and_comments(cur_diff)
        lines = cur_diff.split('\n')
        flag = False  # flag to keep track of logical changes
        for line in lines:
            if line.startswith('+') or line.startswith('-'):
                loc += 1
                if not flag:
                    logical += 1
                    flag = True
            else:
                flag = False
        ind += 2
    return loc, logical
    

def process_commit(projectId, sha, filepath):
    common.switch_dir_to_project_path(projectId)

    affected_files = 0
    net_loc_change = 0
    infile_loc_change = 0
    net_logical_change = 0
    infile_logical_change = 0
    # TODO:affected functions?

    difflog = subprocess.check_output(
        shlex.split("git show "+sha),
        encoding="437"
    )

    filediffs= get_file_diffs(difflog)
    affected_files=len(filediffs)

    for diff in filediffs:
        loc, logical = loc_and_logical_block_change(diff)
        if filepath in diff:
            infile_loc_change = loc
            infile_logical_change = logical
        net_loc_change += loc
        net_logical_change += logical

    return [affected_files, net_loc_change, infile_loc_change, net_logical_change, infile_logical_change]


def update_fix_complexity(projectId):
    alerts = get_alerts(projectId)
    logging.info("%s alerts to be analyzed for fix_complexity",len(alerts))
    for item in alerts:
        sha = item['sha']
        cid = item['idcommits']
        filepath = item['filepath_on_coverity'][1:]
        fid = item['idfiles']
        aid = item['idalerts']
        arguments= [aid, cid]
        
        arguments += process_commit(projectId, sha, filepath)
        
        #get the total number of alerts fixed by this single commit
        query = 'select count(*) as c from actionability where single_fix_commit=%s'
        total_fixed_alerts = sql.execute(query,(cid,))[0]['c']
        arguments.append(total_fixed_alerts)

        query = '''select count(*) as c from 
                actionability ac
                join alert a
                on a.id = ac.alert_id
                where ac.single_fix_commit=%s
                and a.file_id= %s '''
        infile_fixed_alerts = sql.execute(query,(cid,fid))[0]['c']
        arguments.append(infile_fixed_alerts)
        
        query='insert into fix_complexity values(%s,%s,%s,%s,%s,%s,%s,%s,%s)'
        print(sql.execute(query,tuple(arguments),get_affected_rowcount=True)[1])


if __name__ == '__main__':
    update_fix_complexity(1)
