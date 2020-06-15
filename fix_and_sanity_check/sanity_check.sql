-- examples sqls to do some sanity checking on database
select filepath_on_coverity, count(*)
from files 
where project = 'Kodi'
group by filepath_on_coverity
having count(*) > 1;

select file_id 
from alerts 
where file_id not in
(select idfiles from files);