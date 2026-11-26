-- Compare clicks, spend, orders and sales before and after day 20 for the 5 campaigns
-- with the lowest ROAS ratio. Shows which part of the formula changed.
-- Run from the repo root:
--   docker exec -i ads-platform-db-1 psql -U ads < sql/drop_causes.sql
with d as (
  select c.id, c.name,
         (m.metric_date - date '2026-10-01' + 1) >= 20 as late,
         m.impressions, m.clicks, m.spend, m.orders, m.sales
  from daily_metrics m
  join ad a on a.id = m.ad_id
  join ad_group g on g.id = a.ad_group_id
  join campaign c on c.id = g.campaign_id
),
p as (
  select id, name, late,
         sum(clicks)  as clicks,
         sum(spend)   as spend,
         sum(orders)  as orders,
         sum(sales)   as sales,
         sum(impressions) as impressions
  from d
  group by id, name, late
)
select name,
       case when late then 'late (day 20+)' else 'early (day 1-19)' end as period,
       clicks,
       round(spend, 2)  as spend,
       orders,
       round(sales, 2) as sales,
       round(spend / nullif(clicks, 0), 2)  as cpc,
       round(orders::numeric / nullif(clicks, 0), 3) as conversion_rate,
       round(sales / nullif(spend, 0), 2)   as roas
from p
where name in (
  select name from (
    select c.name,
           (sum(m.sales) filter (where (m.metric_date - date '2026-10-01' + 1) >= 20)
             / nullif(sum(m.spend) filter (where (m.metric_date - date '2026-10-01' + 1) >= 20), 0))
         / nullif(sum(m.sales) filter (where (m.metric_date - date '2026-10-01' + 1) < 20)
             / nullif(sum(m.spend) filter (where (m.metric_date - date '2026-10-01' + 1) < 20), 0), 0) as ratio
    from daily_metrics m
    join ad a on a.id = m.ad_id
    join ad_group g on g.id = a.ad_group_id
    join campaign c on c.id = g.campaign_id
    group by c.id, c.name
    order by ratio nulls last
    limit 5
  ) worst
)
order by name, late;
