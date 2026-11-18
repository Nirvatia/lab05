<script>
	import { api } from '#lib/api.js';
	import StudentsTab from '#lib/components/StudentsTab.svelte';
	import GroupsTab from '#lib/components/GroupsTab.svelte';
	import CoursesTab from '#lib/components/CoursesTab.svelte';

	let tab = $state('students');
	let stats = $state(null);
	let seeding = $state(false);
	let refreshKey = $state(0);
	let error = $state('');

	async function loadStats() {
		try {
			stats = await api.stats();
		} catch (e) {
			error = e.message;
		}
	}

	$effect(() => {
		loadStats();
	});

	async function reseed() {
		if (!confirm('Пересоздать тестовые данные? Все текущие данные будут удалены и сгенерированы заново (1000 студентов).')) return;
		seeding = true;
		error = '';
		try {
			await api.seed(1000);
			refreshKey += 1;
			await loadStats();
		} catch (e) {
			error = e.message;
		} finally {
			seeding = false;
		}
	}
</script>

<div class="shell">
	<header class="header">
		<div>
			<h1>Students <span class="accent">ORM</span></h1>
			<p class="muted">Лабораторная работа: таблицы как классы SQLAlchemy → FastAPI → SvelteKit → MySQL</p>
		</div>
		<div class="header-actions">
			<a class="btn" href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">Swagger /docs</a>
			<button class="btn btn-primary" onclick={reseed} disabled={seeding}>
				{seeding ? 'Генерация…' : '↻ Пересоздать данные'}
			</button>
		</div>
	</header>

	{#if error}
		<div class="banner-error">
			<span>{error}</span>
			<button class="btn btn-ghost" onclick={() => (error = '')} aria-label="Скрыть ошибку">✕</button>
		</div>
	{/if}

	{#if stats}
		<div class="stats">
			<div class="stat"><span class="stat-num">{stats.students}</span><span class="stat-label">студентов</span></div>
			<div class="stat"><span class="stat-num">{stats.groups}</span><span class="stat-label">групп</span></div>
			<div class="stat"><span class="stat-num">{stats.courses}</span><span class="stat-label">курсов</span></div>
			<div class="stat"><span class="stat-num">{stats.cards}</span><span class="stat-label">билетов</span></div>
			<div class="stat"><span class="stat-num">{stats.enrollments}</span><span class="stat-label">записей на курсы</span></div>
			<div class="stat"><span class="stat-num">{stats.avg_age ?? '—'}</span><span class="stat-label">средний возраст</span></div>
		</div>
	{/if}

	<nav class="tabs">
		<button class="tab" class:active={tab === 'students'} onclick={() => (tab = 'students')}>Студенты</button>
		<button class="tab" class:active={tab === 'groups'} onclick={() => (tab = 'groups')}>Группы</button>
		<button class="tab" class:active={tab === 'courses'} onclick={() => (tab = 'courses')}>Курсы</button>
	</nav>

	{#key refreshKey}
		{#if tab === 'students'}
			<StudentsTab onchange={loadStats} />
		{:else if tab === 'groups'}
			<GroupsTab onchange={loadStats} />
		{:else}
			<CoursesTab onchange={loadStats} />
		{/if}
	{/key}

	<footer class="muted footer">
		models.py — ORM-ядро (SQLAlchemy, DeclarativeBase). Все запросы к БД выполняются через классы-модели, без ручного SQL.
	</footer>
</div>