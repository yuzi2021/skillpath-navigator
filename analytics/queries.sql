-- SkillPath analytics for PostgreSQL (also uses standard SQL supported by SQLite).
-- Tables come from api/migrations; there is no salary field in this dataset.

-- 1. Top 20 skills by number of distinct job postings.
-- ORM: Skill.objects.annotate(job_count=Count('jobs', distinct=True)).order_by('-job_count')[:20]
SELECT s.skill_name, s.category, COUNT(DISTINCT r.job_id) AS job_count
FROM api_skill AS s
LEFT JOIN api_jobskillrequirement AS r ON r.skill_id = s.skill_name
GROUP BY s.skill_name, s.category
ORDER BY job_count DESC, s.skill_name
LIMIT 20;

-- 2. Skill frequency by category, including skills with zero jobs.
-- ORM: Skill.objects.values('category').annotate(skill_count=Count('skill_name', distinct=True),
--      job_skill_links=Count('jobskillrequirement'))
SELECT s.category, COUNT(DISTINCT s.skill_name) AS skill_count,
       COUNT(r.id) AS job_skill_links
FROM api_skill AS s
LEFT JOIN api_jobskillrequirement AS r ON r.skill_id = s.skill_name
GROUP BY s.category
ORDER BY job_skill_links DESC, s.category;

-- 3. Jobs with the most listed skills, including jobs with no skills.
-- ORM: JobPosting.objects.annotate(skill_count=Count('skills')).order_by('-skill_count')[:20]
SELECT j.job_link, j.title, j.company, COUNT(r.id) AS skill_count
FROM api_jobposting AS j
LEFT JOIN api_jobskillrequirement AS r ON r.job_id = j.job_link
GROUP BY j.job_link, j.title, j.company
ORDER BY skill_count DESC, j.job_link
LIMIT 20;

-- 4. Posting counts by country and work type (no salary data is available).
-- ORM: JobPosting.objects.values('country', 'work_type').annotate(job_count=Count('job_link'))
SELECT country, work_type, COUNT(*) AS job_count
FROM api_jobposting
GROUP BY country, work_type
ORDER BY job_count DESC, country, work_type;
