import common
import sql
import re
import logging
import os
import shlex
import subprocess
import dateutil.parser as dp
from multiprocessing import Pool

def get_fixed_alerts(projectId):
    '''
    The project code is currently designed to have new alerts invalidness
        to be set as 0 (valid by default)
    Before coming to this phase,
        we already invalidate beforeStartDate,externalFile alert, toolErrorSpike.
    After this process,
        we invalidate file renames
        otherwise, keep the defualt validity
    '''
    q = '''select * from alert
        where (is_invalid=0 or is_invalid is null)
        and status = 'Fixed'
        and project_id=%s
        and id not in
        (select alert_id from actionability);'''
    return sql.execute(q, (projectId,))


def get_merged_date(projectId, id, sha, connection=None):
    getMergeDateQuery = 'select merge_date from merge_date where commit_id=%s'
    results = sql.execute(getMergeDateQuery, (id,), connection=connection)
    if results:
        return results[0]['merge_date']

    query = 'select * from commit where id=%s'
    commit = sql.execute(query, (id,), connection=connection)[0]

    common.switch_dir_to_project_path(projectId,connection=connection)
    # when-merged tool by default checks for master branch
    # https://github.com/mhagger/git-when-merged
    lines = subprocess.check_output(
        shlex.split("git when-merged -l "+sha),
        stderr=subprocess.STDOUT, encoding="437").split('\n')
    dateline = None
    direct_commit = False
    for nextLine in lines:
        if bool(re.search('Commit is directly on this branch', nextLine, re.I)):
            direct_commit = True
        if bool(re.match('Date:', nextLine, re.I)):
            dateline = nextLine
            break
    if direct_commit or not dateline:
        if commit['author_date'] > commit['commit_date']:
            # possible rebase
            date = commit['author_date']
        else:
            date = commit['commit_date']
    else:
        date = re.match('Date:(.*)', dateline, re.I).group(1)
        date = date.strip()
        date = dp.parse(date)

    # insert into database and return from database to keep same formatting
    q = 'insert into merge_date values(%s,%s)'
    try:
        sql.execute(q, (id, date), connection=connection)
    except sql.pymysql.IntegrityError as error:
        if error.args[0] == sql.PYMYSQL_DUPLICATE_ERROR:
            logging.info('merge_date already inserted by another process')
            #safely continue
        else:
            exit()
    return sql.execute(getMergeDateQuery, (id,), connection=connection)[0]['merge_date']


def detect_file_rename_delete_in_a_commit(projectId, sha, filepath, change_type):
    if filepath.startswith('/'):
        filepath = filepath[1:]

    if type(change_type) == str and (bool(re.search('MODIFY', change_type, re.I)) or bool(re.search('ADD', change_type, re.I))):
        return 'modified'
    if type(change_type) == str and bool(re.search('RENAME', change_type, re.I)):
        return 'renamed'
    else:
        common.switch_dir_to_project_path(projectId)
        lines = subprocess.check_output(
            shlex.split("git show --summary "+sha),
            stderr=subprocess.STDOUT, encoding="437").split('\n')
        for nextLine in lines:
            # look for only short filename in lines
            nextLine = nextLine.encode('ascii', 'ignore').decode()
            if filepath.split("/")[-1] in nextLine:
                if 'rename' in nextLine:
                    return 'renamed'
                elif 'delete' in nextLine:
                    return 'deleted'
        return None


def new_file_id_after_renaming(projectId, sha, filepath, connection = None):
    if filepath.startswith('/'):
        filepath = filepath[1:]

    common.switch_dir_to_project_path(projectId)
    lines = subprocess.check_output(
        shlex.split("git show --summary "+sha),
        stderr=subprocess.STDOUT, encoding="437").split('\n')

    rename_line = ''
    filename = filepath.split("/")[-1]
    for nextLine in lines:
        # renaming info in commit message can ruin string matching logic
        # however apart from rename, filename, and =>; git info also contain proportion with a %
        # so checking all those 4 conditions in trying to be more accurate
        if filename in nextLine and 'rename' in nextLine and '=>' in nextLine and '%' in nextLine:
            rename_line = nextLine
    try:
        matchlist = re.findall('{[^{}]*}', rename_line)
        # being more restrictive (prolly not necessary) in having {} in this logic
        if len(matchlist) == 1 and '{' in rename_line and '}' in rename_line:
            temp = re.search("{(.*)}", rename_line).group(1)
            temp = temp.split("=>")
            old_file = temp[0].strip()
            new_file = temp[1].strip()
            rename_line = rename_line.strip()
            start = rename_line.find('{')
            end = rename_line.find('}')
            new_filepath = rename_line[:start] + \
                new_file+rename_line[end+1:]
            new_filepath = new_filepath.replace('//', '/')
            new_filepath = new_filepath.split(' ')[1].strip()
            q = 'select id from file where filepath_on_coverity=%s and project_id=%s'
            return common.get_file_id('/'+new_filepath, projectId, connection=connection)
        # when the full name or filepath has been changed
        elif len(matchlist) == 0:
            rename_line = rename_line.strip()
            temp = rename_line.split('=>')
            old_file = temp[0].strip()
            old_file = old_file.split(' ')[1].strip()
            new_file = temp[1].strip()
            new_filepath = new_file.split(' ')[0].strip()
            q = 'select id from file where filepath_on_coverity=%s and project_id=%s'
            return common.get_file_id('/'+new_filepath, projectId, connection=connection)
        else:
            return None
    except Exception as e:
        logging.warn("exception in rename discovery %s %s", e,old_file,new_filepath, rename_line)
        raise Exception("for debugging purposes", e, rename_line)
        return None


def get_transferred_alert_id_while_file_renamed(projectId, sha, filepath, alert_type_id,
                                                last_detected_date, first_not_detected_anymore_date,
                                                connection=None):
    '''
    find out if the alert was transitioned into a new alert_id:
    1) look at the first_not_detected snapshot
    2) if there's a newly detected alert ( first_detected > last snapshot)
    3) and if it's in the renamed file with the same alert_type
    '''
    new_file_id = new_file_id_after_renaming(projectId, sha, filepath, connection=connection)
    if new_file_id:
        q = '''select * from alert where first_detected > %s
            and first_detected <= %s
            and file_id= %s and alert_type_id = %s '''
        results = sql.execute(
            q, (last_detected_date, first_not_detected_anymore_date, new_file_id, alert_type_id), connection=connection)
        if results:
            return results[0]['id']
    return None


def search_suppression_keywords_in_commit_diffs(projectId, sha, filepath):
    keywords = [
        r'coverity\[.*\]',
        r'/\* fall through \*/',
        '#if defined(__COVERITY__)',
        '@OverridersMustCall', '@OverridersNeedNotCall',
        '@CheckReturnValue',
        '@GuardedBy',
        '@SuppressWarnings',
        '@CheckForNull',
        '@Tainted', '@NotTainted',
        '@SensitiveData',
    ]

    common.switch_dir_to_project_path(projectId)
    if filepath.startswith('/'):
        filepath = filepath[1:]
    lines = subprocess.check_output(
        shlex.split('git show '+sha+' -- '+filepath),
        stderr=subprocess.STDOUT, encoding="437").split("\n")

    for nextLine in lines:
        if bool(re.match('\+', nextLine, re.I)):
            for keyword in keywords:
                if bool(re.search(keyword, nextLine, re.I)):
                    # found suppression word
                    if keyword == r'coverity\[.*\]':
                        temp = re.search(
                            r'coverity\[(.*)\]', nextLine, re.I).group(1)
                        return 'coverity['+temp+']'
                    elif keyword == r'/\* fall through \*/':
                        return '/* fall through */'
                    else:
                        return keyword
        else:
            pass
    return None


def process_alert(alert):
    aid = alert["id"]
    projectId=alert['project_id']
    conn=sql.create_db_connection()
    # initialize actionability columns with default values
    actionability = 0  # keep default at 0, if actionability found change to 1
    marked_bug = None
    file_activity_around_fix = None
    single_fix_commit = None
    fix_commits = None
    deleted = None
    delete_commit = None
    renamed = None
    rename_commit = None
    transfered_alert_id = None
    suppression = None
    suppress_keyword = None
    suppress_commit = None

    classification = alert['classification']
    if bool(re.search('Bug', classification, re.I)):
        marked_bug = 'yes'

    first_detected_date = alert['first_detected']
    # Note: add 00:00:00 and 23:59:59 later with next two as search window
    last_detected_date = common.get_snapshot_date(
        projectId, alert['last_snapshot_id'], connection=conn)
    last_detected_date = last_detected_date.replace(
        hour=0, minute=0, second=0)
    first_not_detected_anymore_date = common.get_snapshot_date(
        projectId, 
        common.get_next_snapshotId(projectId, alert['last_snapshot_id'], connection=conn),
        connection=conn)
    first_not_detected_anymore_date = first_not_detected_anymore_date.replace(
        hour=23, minute=59, second=59)

    fileId = alert["file_id"]
    filepath = sql.execute('select filepath_on_coverity from file where id=%s', (fileId,),connection=conn)[0]['filepath_on_coverity']
    # look at if there's a commit (both author and commit date) within
    # first_detected and first_not_detected
    q = '''select c.id as idcommits, c.*, fc.*
        from filecommit fc
        join commit c on fc.commit_id = c.id
        where fc.file_id=%s
        and ((c.commit_date >= %s  and c.commit_date <= %s)
        or (c.author_date >= %s and c.author_date <= %s)) '''
    potential_commits = sql.execute(q, (fileId, first_detected_date, first_not_detected_anymore_date,
                                        first_detected_date, first_not_detected_anymore_date),
                                    connection=conn)

    '''
    for each commit also get the merged date
    if merging date into master is when the alert is fixed, then they are fix commits 
    '''
    merged_commits = []
    if potential_commits:
        for item in potential_commits:
            merge_date = get_merged_date(
                projectId, item['idcommits'], item['sha'], connection=conn)
            item['merge_date'] = merge_date
            if merge_date >= last_detected_date and merge_date <= first_not_detected_anymore_date:
                merged_commits.append(item)

    # if marked_bug == 'yes' and not merged_commits:
    #     raise Exception("marked bug but no fix commits found", aid, fileId)

    if merged_commits:
        file_activity_around_fix = 'yes'

        # check if the file is deleted or renamed (involved moved) in the last commit
        last_commit = merged_commits[-1]
        changeType = detect_file_rename_delete_in_a_commit(projectId, last_commit['sha'],
                                                            filepath, last_commit['change_type'])
        if changeType == 'deleted':
            deleted = 'yes'
            delete_commit = last_commit['idcommits']
        elif changeType == 'renamed':
            renamed = 'yes'
            transfered_alert_id = get_transferred_alert_id_while_file_renamed(projectId,
                                    last_commit['sha'], filepath,alert['alert_type_id'],
                                    last_detected_date, first_not_detected_anymore_date, connection=conn)
        else:
            commits = []
            for item in merged_commits:
                c = {}
                c['commit_id'] = item['idcommits']
                c['sha'] = item['sha']
                c['filepath'] = filepath[1:]
                c['msg'] = item['message']
                commits.append(c)
            for c in commits:
                # look for suppression keywords in commit diff
                suppression_word = search_suppression_keywords_in_commit_diffs(
                    projectId, c['sha'], c['filepath'])
                if suppression_word:
                    suppression = 'yes'
                    suppress_commit = c['commit_id']
                    suppress_keyword = suppression_word
                    break
            if not suppress_commit:
                # developer fix
                if len(commits) == 1:
                    single_fix_commit = commits[0]['commit_id']
                else:
                    # look for keyword coverity, CID
                    temp = []
                    for c in commits:
                        temp.append(str(c['commit_id']))
                        if (bool(re.search('coverity', c['msg'], re.I))) or (bool(re.search('CID[\s0-9]', c['msg'], re.I))):
                            single_fix_commit = c['commit_id']
                    fix_commits = ','.join(temp)

    # determine actionability
    if marked_bug == 'yes' or single_fix_commit or fix_commits:
        actionability = 1
    arguments = [aid, actionability, marked_bug, file_activity_around_fix, single_fix_commit, fix_commits, deleted,
                    delete_commit, renamed, rename_commit, transfered_alert_id, suppression, suppress_commit, suppress_keyword]

    q = 'insert into actionability values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'
    sql.execute(q, tuple(arguments),connection=conn)
    logging.info('analyzed %s',aid)


def main_file_actionability(projectId):
    alerts = get_fixed_alerts(projectId)
    logging.info("new alerts to analyze: %s for project %s",
                 len(alerts), common.get_repo_name(projectId))
    
    
    for alert in alerts:
        alert['project_id']=projectId
    
    pool=Pool(os.cpu_count())
    pool.map(process_alert,alerts)
    
    
def invalidate_file_renamed_alerts():
    '''look for alerts in actionability that has renamed 'yes'
    and invalidate them to 4 in alerts '''
    query = '''update alert 
        set is_invalid=4
        where id in 
        (select alert_id from actionability 
        where file_renamed="yes")'''
    affectedCount = sql.execute(query, get_affected_rowcount=True)[1]
    logging.info("%s alerts invalidated due to file renaming", affectedCount)

    '''if they have a transferred alert id then adjust first_detected'''
    query = '''select * from actionability ac
            join alert a
            on a.id = ac.alert_id
            where ac.file_renamed='yes'
            and transfered_alert_id is not null;'''
    results = sql.execute(query)
    updated = 0
    for item in results:
        old_id = item['alert_id']
        new_id = item['transfered_alert_id']
        query = '''update alert
                set first_detected=(
                select first_detected from 
                (select first_detected from alert
                where id = %s) as sub)
                where id=%s'''
        updated += sql.execute(query, (old_id, new_id),
                               get_affected_rowcount=True)[1]
    logging.info("%s alerts information updated due to file renaming", updated)


def analyze_actionability(projectId):
    main_file_actionability(projectId)
    invalidate_file_renamed_alerts()


if __name__ == '__main__':
    '''
    the current code determines actionability based on only the affected file's activity
    the code can be extended to consider multiple files (if involved) if such data is available
    '''
    main_file_actionability(1)
