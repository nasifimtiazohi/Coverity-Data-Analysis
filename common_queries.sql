-- documentation of some common queries 

-- get the latest snapshot Id for each project in database
select project_id,id, date
from snapshot s1
where date =( select max(date)
    from snapshot s2
    where s2.project_id=s1.project_id);



