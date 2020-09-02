select *
from
(select *
from memory_cwe
union
select distinct a.CWE, avg(memory)
from alert_type at
join alert a on at.id = a.alert_type_id
join memory_error me on at.id = me.alert_type_id
group by a.CWE) sub
join cwe c on sub.CWE=c.id;