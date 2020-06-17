import common, sql
import re


# first look for file_activity with the main affected file
def main_file_actionability(projectId):
    q='''select * from alert
        where is_invalid is null
        and status = 'Fixed'
        and project_id=%s;'''
    alerts=sql.execute(q,(projectId,))
    print("new alerts to analyze: ",len(alerts), " for project "+common.get_repo_name(projectId))

    for alert in alerts:
        aid=alert["id"]
        # initialize actionability columns with default values
        actionability=0 #keep default at 0, if actionability found change to 1
        marked_bug=None
        file_activity_around_fix=None
        single_fix_commit=None
        fix_commits=None
        deleted=None
        delete_commit=None
        renamed=None
        rename_commit=None
        transfered_alert_id=None
        suppression=None
        suppress_keyword=None
        suppress_commit=None
        
        classification=alert['classification']
        if bool(re.search('Bug',classification,re.I)):
                marked_bug='yes'

        first_detected_date=alert['first_detected']
        #Note: add 00:00:00 and 23:59:59 later with next two as search window
        last_detected_date=common.get_snapshot_date(projectId, alert['last_snapshot_id'])
        last_detected_date=last_detected_date.replace(hour=0,minute=0,second=0)
        first_not_detected_anymore_date=common.get_snapshot_date(projectId, common.get_next_snapshotId(projectId,alert['last_snapshot_id'] ))
        first_not_detected_anymore_date=first_not_detected_anymore_date.replace(hour=23,minute=59,second=59)
        print(first_detected_date,last_detected_date,first_not_detected_anymore_date)
        
        fileId=alert["file_id"]
        # look at if there's a commit (both author and commit date) within 
        # first_detected and first_not_detected
        q='''select *
            from filecommit fc
            join commit c on fc.commit_id = c.id
            where fc.file_id=%s
            and ((c.commit_date >= %s  and c.commit_date <= %s)
            or (c.author_date >= %s and c.author_date <= %s)) '''
        results=sql.execute(q,(fileId, first_detected_date,first_not_detected_anymore_date,
                                first_detected_date,first_not_detected_anymore_date))
        print(alert['cid'], fileId, results)
        

        # merged_commits=[]
        # if results:
        #     # for each commit also get the merged date
        #     for item in results:
        #         merge_date=get_merged_date(item['idcommits'],item['sha'])
        #         item['merge_date']=merge_date
        #         if merge_date>=last_detected_date and merge_date<=first_not_detected_anymore_date:
        #                 merged_commits.append(item)
        # results=merged_commits #need to refactor this
        # if len(results)>0:
        #         file_activity_around_fix='yes'

        #         # check if the file is deleted or renamed (involved moved) in the last commit
        #         last_commit=results[-1]
        #         temp=detect_file_rename_delete_in_a_commit(last_commit['sha'],last_commit['filepath_on_coverity'],last_commit['change_type'])
        #         if temp == 'deleted':
        #                 deleted='yes'
        #                 delete_commit=str(last_commit['idcommits'])
        #         elif temp == 'renamed':
        #                 # find out if the alert was transitioned into a new alert_id
        #                 # how?
        #                 # look at the first_not_detected snapshot
        #                 # if there's a newly detected alert ( first_detected > last snapshot)
        #                 # and if it's in the renamed file with the same alert_type
        #                 renamed='yes'
        #                 rename_commit=str(last_commit['idcommits'])
        #                 new_file_id=new_file_id_after_renaming(last_commit['sha'],last_commit['filepath_on_coverity'])
        #                 if new_file_id:
        #                         query="select * from alerts where first_detected > '"+last_detected_date+"' and first_detected <= '"+first_not_detected_anymore_date+"' \
        #                                 and file_id="+str(new_file_id) +" and bug_type="+str(alert['bug_type'])+";"
        #                         temp_results=execute(query)
        #                         if len(temp_results)==1:
        #                                 transfered_alert_id=temp_results[0]['idalerts']
        #         else:
        #                 commits=[]
        #                 for item in results:
        #                         c={}
        #                         c['commit_id']=item['idcommits']
        #                         c['sha']=item['sha']
        #                         c['filepath']=item['filepath_on_coverity'][1:]
        #                         c['msg']=item['message']
        #                         commits.append(c)
        #                 for c in commits:
        #                         # look for suppression keywords in commit diff
        #                         suppression_word=search_suppression_keywords_in_commit_diffs(c['sha'],c['filepath'])
        #                         if suppression_word!=None:
        #                                 suppression='yes'
        #                                 suppress_commit=str(c['commit_id'])
        #                                 suppress_keyword=suppression_word
        #                                 break
        #                 if suppress_commit==None:
        #                         # developer fix
        #                         if len(commits)==1:
        #                                 single_fix_commit=str(commits[0]['commit_id'])
        #                         else:
        #                                 # look for keyword coverity, CID
        #                                 temp=[]
        #                                 for c in commits:
        #                                         temp.append(str(c['commit_id']))
        #                                         if (bool(re.search('coverity',c['msg'],re.I))) or (bool(re.search('CID[\s0-9]',c['msg'],re.I))):
        #                                                 single_fix_commit=str(c['commit_id'])
        #                                 fix_commits=','.join(temp)
                
        # # determine actionability
        # if marked_bug=='yes' or single_fix_commit!=None or fix_commits!=None:
        #         actionability=1
        # # print((str(aid),actionability,marked_bug,file_activity_around_fix,single_fix_commit,fix_commits,deleted, 
        # #         delete_commit,renamed,rename_commit,transfered_alert_id,suppression,suppress_commit,suppress_keyword))
        # try:
        #         with connection.cursor() as cursor:
        #                 cursor.execute('insert into actionability values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', 
        #                 (str(aid),actionability,marked_bug,file_activity_around_fix,single_fix_commit,fix_commits,deleted, 
        #                 delete_commit,renamed,rename_commit,transfered_alert_id,suppression,suppress_commit,suppress_keyword))
        #                 print(str(aid))
        # except Exception as e:
        #         print("hello",e)

if __name__=='__main__':
    main_file_actionability(1)