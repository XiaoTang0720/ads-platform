-- Find campaigns whose ROAS fell after day 20 (ROAS = sales / spend).
-- Run from the repo root:
--   docker exec -i ads-platform-db-1 psql -U ads < sql/roas_drops.sql
with d as (
  select c.id, c.name,
         (m.metric_date - date '2026-10-01' + 1) >= 20 as late,
         m.sales, m.spend
  from daily_metrics m
  join ad a on a.id = m.ad_id
  join ad_group g on g.id = a.ad_group_id
  join campaign c on c.id = g.campaign_id
)
select name,
       round(sum(sales) filter (where not late) / nullif(sum(spend) filter (where not late), 0), 2) as roas_early,
       round(sum(sales) filter (where late)     / nullif(sum(spend) filter (where late), 0), 2)     as roas_late,
       round((sum(sales) filter (where late) / nullif(sum(spend) filter (where late), 0))
           / nullif(sum(sales) filter (where not late) / nullif(sum(spend) filter (where not late), 0), 0), 2) as ratio
from d
group by id, name
order by ratio nulls last
limit 5;
