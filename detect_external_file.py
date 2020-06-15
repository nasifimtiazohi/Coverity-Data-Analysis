'''after searching for file commits within start and end date range,
look for other files if they have any commit ever in history,
as prior check could miss some due to date range.
If yes, PUT ONE IN FILE COMMIT FOR INDICATION.
If no, then files that have no commits in filecommits,
we will know that they are non-project files'''
import common, sql
import sys
import datetime
import re
import os
import subprocess
import re
import shlex
import dateutil.parser as dp
import add_commits as ac

def get_potential_files(projectId):
    q='''select *
        from file f
        join alert a
            on f.id = a.file_id
            and a.project_id=f.project_id
        where f.project_id=%s
        and (a.is_invalid=0 or a.is_invalid is null)
        and f.is_processed is null; '''
    return sql.execute(q,(projectId,))



def detect_external_file_and_put_one_commit_to_db_for_internals(projectId):
    files= get_potential_files(projectId)
    for item in files:
        filepath=item['filepath_on_coverity'][1:]
        fileId=item['id']
        #search for only one commit
        lines = subprocess.check_output(
                shlex.split('git log --follow --pretty=fuller --stat -n 1 \
                -- '+filepath), 
                stderr=subprocess.STDOUT,
                encoding="437"
                ).split('\n')
        count=len(lines)-1
        if count==0:
            print("external file found: ", filepath)
        else:
            commits=ac.process_commits(lines)
            ac.add_commits_and_filecommits(projectId,fileId,commits)

if __name__=='__main__':
    # TODO: make paralellize and run for all projects at once

    #read command line arguments
    #TODO: might just make it over all projects when paralellized
    project=sys.argv[1]
    projectId=common.get_project_id(project)

    path="/Users/nasifimtiaz/Desktop/repos_coverity/"+common.get_repo_name(projectId)
    os.chdir(path)
    
    detect_external_file_and_put_one_commit_to_db_for_internals(projectId)

    