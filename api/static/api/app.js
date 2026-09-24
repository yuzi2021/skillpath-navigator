/* SkillPath's browser layer: same-origin requests to the existing REST API. */
(() => {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const endpoints = {
    demand: '/api/skills/most-demanded/',
    role: '/api/skills/for-role/',
    match: '/api/jobs/by-skills/',
    combinations: '/api/skills/combinations/',
    bookmarks: '/api/bookmarks/',
  };
  const statuses = ['interested', 'applied', 'interviewing', 'offered', 'rejected'];
  let nextBookmarksPage = null;
  let shownBookmarks = 0;
  let demandSkills = [];
  let demandExpanded = false;

  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function setState(id, message, kind = '') {
    const element = $(id);
    element.textContent = message;
    element.classList.toggle('is-error', kind === 'error');
    element.classList.toggle('is-success', kind === 'success');
  }

  function errorText(data, fallback) {
    if (!data || typeof data !== 'object') return fallback;
    if (typeof data.error === 'string') return data.error;
    if (typeof data.detail === 'string') return data.detail;
    const first = Object.values(data)[0];
    if (Array.isArray(first)) return first.join(' ');
    if (typeof first === 'string') return first;
    return fallback;
  }

  async function request(path, options = {}) {
    const url = new URL(path, window.location.origin);
    if (url.origin !== window.location.origin) throw new Error('Unexpected API address.');
    const headers = { Accept: 'application/json', ...(options.headers || {}) };
    const method = (options.method || 'GET').toUpperCase();
    if (!['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method)) {
      headers['X-CSRFToken'] = document.querySelector('[name=csrfmiddlewaretoken]').value;
    }
    if (options.body) headers['Content-Type'] = 'application/json';
    const response = await fetch(url, { credentials: 'same-origin', ...options, headers });
    const data = await response.json().catch(() => null);
    if (!response.ok) throw new Error(errorText(data, `Request failed (${response.status}).`));
    return data;
  }

  function queryUrl(path, params) {
    return `${path}?${new URLSearchParams(params)}`;
  }

  function categoryLabel(value) {
    return String(value || 'Uncategorized').replaceAll('_', ' ').toLowerCase();
  }

  function renderSkills(items, listId, countKey, metric, widthValue) {
    const list = $(listId);
    list.replaceChildren();
    const maximum = Math.max(1, ...items.map((item) => Number(item[countKey]) || 0));
    for (const item of items) {
      const row = node('li', 'skill-row');
      const top = node('div', 'skill-row-top');
      top.append(node('span', 'skill-name', item.skill_name), node('span', 'skill-meta', metric(item)));
      const category = node('p', 'skill-category', categoryLabel(item.category));
      const track = node('div', 'bar-track');
      track.setAttribute('aria-hidden', 'true');
      const fill = node('div', 'bar-fill');
      const width = widthValue ? widthValue(item) : (Number(item[countKey]) / maximum) * 100;
      fill.style.width = `${Math.max(0, Math.min(100, width || 0))}%`;
      track.append(fill);
      row.append(top, category, track);
      list.append(row);
    }
  }

  async function loadDemand() {
    setState('demand-state', 'Loading skills…');
    try {
      const skills = await request(endpoints.demand);
      if (!skills.length) {
        setState('demand-state', 'No skill data is loaded yet.');
        return;
      }
      demandSkills = skills;
      renderSkills(skills.slice(0, 8), 'demand-list', 'job_count',
        (item) => `${item.job_count} ${item.job_count === 1 ? 'job' : 'jobs'}`);
      $('demand-show-more').hidden = skills.length <= 8;
      $('demand-show-more').textContent = `Show all ${skills.length} skills`;
      setState('demand-state', '');
    } catch (error) {
      setState('demand-state', `Could not load skills: ${error.message}`, 'error');
    }
  }

  async function exploreRole(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector('button');
    const role = $('role-select').value;
    $('role-list').replaceChildren();
    $('role-summary').textContent = '';
    setState('role-state', 'Looking at this role…');
    button.disabled = true;
    try {
      const data = await request(queryUrl(endpoints.role, { role }));
      const count = Number(data.matching_jobs_count) || 0;
      $('role-summary').textContent = `${count} ${count === 1 ? 'posting' : 'postings'} matched this role in the snapshot.`;
      if (!count || !data.top_skills.length) {
        setState('role-state', 'No skill results for this role in the current dataset. Try another role.');
        return;
      }
      renderSkills(data.top_skills, 'role-list', 'job_count',
        (item) => `${item.job_count} ${item.job_count === 1 ? 'job' : 'jobs'}`);
      setState('role-state', '');
    } catch (error) {
      setState('role-state', `Could not explore this role: ${error.message}`, 'error');
    } finally {
      button.disabled = false;
    }
  }

  function safeJobUrl(raw) {
    try {
      const url = new URL(raw);
      return ['http:', 'https:'].includes(url.protocol) ? url.href : null;
    } catch (_) {
      return null;
    }
  }

  function jobCard(job) {
    const card = node('article', 'job-card');
    const top = node('div', 'job-card-top');
    const titleBlock = node('div');
    titleBlock.append(node('h4', '', job.title), node('p', 'job-company', job.company));
    top.append(titleBlock, node('span', 'match-score', `${Number(job.match_score).toFixed(1)}% fit`));
    const meta = node('div', 'job-meta');
    for (const value of [job.location, job.work_type, job.experience_level]) {
      if (value) meta.append(node('span', '', value));
    }
    const details = node('p', 'job-details',
      `${job.matched_skills_count} of ${job.required_skills_count} listed skills matched`);
    const actions = node('div', 'job-actions');
    const save = node('button', 'button button-outline', 'Save this job');
    save.type = 'button';
    save.addEventListener('click', () => {
      $('bookmark-job-link').value = job.job_link;
      $('bookmarks').scrollIntoView({ behavior: 'smooth' });
      $('bookmark-job-link').focus({ preventScroll: true });
      setState('bookmark-form-state', 'Job URL added. Add a note or save it to your tracker.', 'success');
    });
    actions.append(save);
    const url = safeJobUrl(job.job_link);
    if (url) {
      const link = node('a', '', 'Open posting ↗');
      link.href = url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      actions.append(link);
    }
    card.append(top, meta, details, actions);
    return card;
  }

  async function matchSkills(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector('button');
    const skills = $('skills-input').value.trim();
    if (!skills) return;
    $('match-results').replaceChildren();
    $('match-summary').textContent = '';
    setState('match-state', 'Finding matches…');
    button.disabled = true;
    try {
      const data = await request(queryUrl(endpoints.match, { skills }));
      const jobs = data.jobs || [];
      if (!jobs.length) {
        setState('match-state', 'No jobs matched those skills. Try a broader or different skill name.');
        return;
      }
      for (const job of jobs) $('match-results').append(jobCard(job));
      $('match-summary').textContent = `Showing ${jobs.length} ranked ${jobs.length === 1 ? 'job' : 'jobs'} (up to 50).`;
      setState('match-state', '');
    } catch (error) {
      setState('match-state', `Could not find matches: ${error.message}`, 'error');
    } finally {
      button.disabled = false;
    }
  }

  async function exploreCombinations(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector('button');
    const skill = $('base-skill-input').value.trim();
    if (!skill) return;
    $('combination-list').replaceChildren();
    $('combination-summary').textContent = '';
    setState('combination-state', 'Looking for skill pairings…');
    button.disabled = true;
    try {
      const data = await request(queryUrl(endpoints.combinations, { skill }));
      const count = Number(data.total_jobs_with_skill) || 0;
      $('combination-summary').textContent = `${count} ${count === 1 ? 'posting' : 'postings'} mention ${data.base_skill}.`;
      if (!data.commonly_paired_skills.length) {
        setState('combination-state', 'No paired skills found in these postings.');
        return;
      }
      renderSkills(data.commonly_paired_skills, 'combination-list', 'co_occurrence_count',
        (item) => `${item.percentage}% · ${item.co_occurrence_count} jobs`,
        (item) => Number(item.percentage));
      setState('combination-state', '');
    } catch (error) {
      setState('combination-state', `Could not load pairings: ${error.message}`, 'error');
    } finally {
      button.disabled = false;
    }
  }

  function statusSelect(current, id) {
    const select = node('select');
    select.id = id;
    select.name = 'status';
    select.required = true;
    if (!statuses.includes(current)) {
      const placeholder = node('option', '', `Current status: ${current} — choose a new status`);
      placeholder.value = '';
      placeholder.disabled = true;
      placeholder.selected = true;
      select.append(placeholder);
    }
    for (const status of statuses) {
      const option = node('option', '', status[0].toUpperCase() + status.slice(1));
      option.value = status;
      option.selected = status === current;
      select.append(option);
    }
    return select;
  }

  function bookmarkCard(bookmark) {
    const card = node('article', 'bookmark-card');
    const top = node('div', 'bookmark-card-top');
    const titleBlock = node('div');
    titleBlock.append(node('h4', '', bookmark.job_title),
      node('p', 'bookmark-card-subtitle', [bookmark.job_company, bookmark.job_location].filter(Boolean).join(' · ')));
    top.append(titleBlock, node('span', 'status-badge', bookmark.status));

    const form = node('form', 'bookmark-edit-form');
    const notesField = node('div', 'notes-field');
    const notesId = `bookmark-notes-${bookmark.id}`;
    const notesLabel = node('label', '', 'Notes');
    notesLabel.htmlFor = notesId;
    const notes = node('textarea');
    notes.id = notesId;
    notes.name = 'notes';
    notes.rows = 2;
    notes.value = bookmark.notes || '';
    notesField.append(notesLabel, notes);

    const statusField = node('div');
    const statusId = `bookmark-status-${bookmark.id}`;
    const statusLabel = node('label', '', 'Status');
    statusLabel.htmlFor = statusId;
    const select = statusSelect(bookmark.status, statusId);
    statusField.append(statusLabel, select);

    const actions = node('div', 'bookmark-card-actions');
    const save = node('button', 'button button-dark', 'Save changes');
    save.type = 'submit';
    const remove = node('button', 'button button-danger', 'Delete');
    remove.type = 'button';
    const message = node('span', 'state');
    message.setAttribute('role', 'status');
    message.setAttribute('aria-live', 'polite');
    actions.append(save, remove, message);
    form.append(notesField, statusField, actions);

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      save.disabled = true;
      message.textContent = 'Saving…';
      message.className = 'state';
      try {
        await request(`${endpoints.bookmarks}${bookmark.id}/`, {
          method: 'PATCH', body: JSON.stringify({ notes: notes.value, status: select.value }),
        });
        await loadBookmarks(true);
        setState('bookmark-form-state', 'Bookmark updated.', 'success');
      } catch (error) {
        message.textContent = `Could not save: ${error.message}`;
        message.classList.add('is-error');
      } finally {
        save.disabled = false;
      }
    });

    remove.addEventListener('click', async () => {
      if (!window.confirm(`Delete the bookmark for ${bookmark.job_title}?`)) return;
      remove.disabled = true;
      message.textContent = 'Deleting…';
      message.className = 'state';
      try {
        await request(`${endpoints.bookmarks}${bookmark.id}/`, { method: 'DELETE' });
        await loadBookmarks(true);
        setState('bookmark-form-state', 'Bookmark deleted.', 'success');
      } catch (error) {
        message.textContent = `Could not delete: ${error.message}`;
        message.classList.add('is-error');
      } finally {
        remove.disabled = false;
      }
    });

    card.append(top, form);
    return card;
  }

  async function loadBookmarks(reset = false) {
    if (reset) {
      $('bookmark-list').replaceChildren();
      shownBookmarks = 0;
      nextBookmarksPage = endpoints.bookmarks;
    }
    if (!nextBookmarksPage) return;
    const button = $('bookmark-load-more');
    button.disabled = true;
    setState('bookmark-state', 'Loading bookmarks…');
    try {
      const data = await request(nextBookmarksPage);
      const items = data.results || [];
      for (const bookmark of items) $('bookmark-list').append(bookmarkCard(bookmark));
      shownBookmarks += items.length;
      nextBookmarksPage = data.next || null;
      button.hidden = !nextBookmarksPage;
      const total = Number(data.count ?? data.statistics?.total ?? shownBookmarks);
      $('bookmark-count').textContent = `${total} saved`;
      if (shownBookmarks === 0) {
        setState('bookmark-state', 'No bookmarks yet. Find a matching job or paste a job URL to start.');
      } else {
        setState('bookmark-state', `Showing ${shownBookmarks} of ${total} saved opportunities.`);
      }
    } catch (error) {
      setState('bookmark-state', `Could not load bookmarks: ${error.message}`, 'error');
    } finally {
      button.disabled = false;
    }
  }

  async function createBookmark(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector('button[type=submit]');
    button.disabled = true;
    setState('bookmark-form-state', 'Saving bookmark…');
    try {
      await request(endpoints.bookmarks, {
        method: 'POST',
        body: JSON.stringify({
          job_link: $('bookmark-job-link').value.trim(),
          notes: $('bookmark-notes').value.trim(),
          status: $('bookmark-status').value,
        }),
      });
      form.reset();
      setState('bookmark-form-state', 'Job saved to your tracker.', 'success');
      await loadBookmarks(true);
    } catch (error) {
      setState('bookmark-form-state', `Could not save bookmark: ${error.message}`, 'error');
    } finally {
      button.disabled = false;
    }
  }

  $('role-form').addEventListener('submit', exploreRole);
  $('demand-show-more').addEventListener('click', () => {
    demandExpanded = !demandExpanded;
    renderSkills(demandExpanded ? demandSkills : demandSkills.slice(0, 8),
      'demand-list', 'job_count',
      (item) => `${item.job_count} ${item.job_count === 1 ? 'job' : 'jobs'}`);
    $('demand-show-more').textContent = demandExpanded
      ? 'Show fewer skills' : `Show all ${demandSkills.length} skills`;
  });
  $('matcher-form').addEventListener('submit', matchSkills);
  $('combination-form').addEventListener('submit', exploreCombinations);
  $('bookmark-create-form').addEventListener('submit', createBookmark);
  $('bookmark-load-more').addEventListener('click', () => loadBookmarks(false));
  loadDemand();
  loadBookmarks(true);
})();
