<script>
	import { api } from '#lib/api.js';
	import Modal from './Modal.svelte';

	let { onchange = () => {} } = $props();

	const LIMIT = 20;
	let students = $state([]);
	let total = $state(0);
	let page = $state(0);
	let search = $state('');
	let groupFilter = $state('');
	let groups = $state([]);
	let courses = $state([]);
	let loading = $state(false);
	let busy = $state(false);
	let error = $state('');
	let expanded = $state(null);
	let form = $state(null);
	let cardFor = $state(null);
	let cardNumber = $state('');
	let enrollChoice = $state('');

	async function load() {
		loading = true;
		error = '';
		try {
			const data = await api.students({
				limit: LIMIT,
				offset: page * LIMIT,
				search,
				group_id: groupFilter
			});
			if (data.items.length === 0 && page > 0 && data.total > 0) {
				page -= 1;
				return;
			}
			students = data.items;
			total = data.total;
		} catch (e) {
			error = e.message;
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		const deps = [search, groupFilter, page];
		const t = setTimeout(load, deps[0] ? 300 : 0);
		return () => clearTimeout(t);
	});

	$effect(() => {
		api.groups().then((g) => (groups = g)).catch(() => {});
		api.courses().then((c) => (courses = c)).catch(() => {});
	});

	async function mutate(fn) {
		busy = true;
		error = '';
		try {
			await fn();
			await load();
			onchange();
		} catch (e) {
			error = e.message;
		} finally {
			busy = false;
		}
	}

	function toggle(s) {
		expanded = expanded === s.student_id ? null : s.student_id;
		enrollChoice = '';
	}

	function openCreate() {
		form = { id: null, name: '', email: '', age: 18, group_id: '' };
	}

	function openEdit(s) {
		form = { id: s.student_id, name: s.name, email: s.email, age: s.age, group_id: s.group_id ?? '' };
	}

	async function saveStudent(e) {
		e.preventDefault();
		const payload = {
			name: form.name.trim(),
			email: form.email.trim(),
			age: Number(form.age),
			group_id: form.group_id === '' ? null : Number(form.group_id)
		};
		busy = true;
		error = '';
		try {
			if (form.id) await api.updateStudent(form.id, payload);
			else await api.createStudent(payload);
			form = null;
			await load();
			onchange();
		} catch (err) {
			error = err.message;
		} finally {
			busy = false;
		}
	}

	function removeStudent(s) {
		if (!confirm(`Удалить студента «${s.name}»? Его билет и записи на курсы тоже будут удалены.`)) return;
		mutate(() => api.deleteStudent(s.student_id));
	}

	function openCard(s) {
		cardFor = s;
		cardNumber = 'ST-' + Math.floor(100000 + Math.random() * 900000);
	}

	async function saveCard(e) {
		e.preventDefault();
		busy = true;
		error = '';
		try {
			await api.createCard({ card_number: cardNumber.trim(), student_id: cardFor.student_id });
			cardFor = null;
			await load();
			onchange();
		} catch (err) {
			error = err.message;
		} finally {
			busy = false;
		}
	}

	function removeCard(s) {
		if (!confirm(`Удалить билет ${s.card.card_number}?`)) return;
		mutate(() => api.deleteCard(s.card.card_id));
	}

	function availableCourses(s) {
		const taken = new Set(s.courses.map((c) => c.course_id));
		return courses.filter((c) => !taken.has(c.course_id));
	}

	function enrollStudent(s) {
		if (!enrollChoice) return;
		const courseId = Number(enrollChoice);
		enrollChoice = '';
		mutate(() => api.enroll({ student_id: s.student_id, course_id: courseId }));
	}

	function unenrollStudent(s, c) {
		mutate(() => api.unenroll(s.student_id, c.course_id));
	}

	function fmtDate(iso) {
		return new Date(iso).toLocaleDateString('ru-RU');
	}
</script>

<div class="toolbar">
	<input
		class="input"
		type="search"
		placeholder="Поиск по имени или email…"
		bind:value={search}
		oninput={() => (page = 0)}
	/>
	<select class="input" bind:value={groupFilter} onchange={() => (page = 0)}>
		<option value="">Все группы</option>
		{#each groups as g (g.group_id)}
			<option value={g.group_id}>{g.name}</option>
		{/each}
	</select>
	<button class="btn btn-primary" onclick={openCreate}>+ Добавить студента</button>
</div>

{#if error}
	<div class="banner-error">
		<span>{error}</span>
		<button class="btn btn-ghost" onclick={() => (error = '')} aria-label="Скрыть ошибку">✕</button>
	</div>
{/if}

<div class="table-wrap">
	<table class="table">
		<thead>
			<tr>
				<th>ID</th>
				<th>Имя</th>
				<th>Email</th>
				<th>Возраст</th>
				<th>Группа</th>
				<th>Билет</th>
				<th>Курсы</th>
				<th></th>
			</tr>
		</thead>
		<tbody>
			{#each students as s (s.student_id)}
				<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
				<tr class="row-main" class:expanded={expanded === s.student_id} onclick={() => toggle(s)}>
					<td><span class="chevron" class:open={expanded === s.student_id}>▶</span> {s.student_id}</td>
					<td>{s.name}</td>
					<td class="muted">{s.email}</td>
					<td>{s.age}</td>
					<td>{s.group ? s.group.name : '—'}</td>
					<td>{s.card ? s.card.card_number : '—'}</td>
					<td>{s.courses.length}</td>
					<td>
						<div class="actions">
							<button
								class="btn btn-sm"
								onclick={(e) => {
									e.stopPropagation();
									openEdit(s);
								}}>Изменить</button
							>
							<button
								class="btn btn-sm btn-danger"
								onclick={(e) => {
									e.stopPropagation();
									removeStudent(s);
								}}>Удалить</button
							>
						</div>
					</td>
				</tr>
				{#if expanded === s.student_id}
					<tr class="detail-row">
						<td colspan="8">
							<div class="detail-grid">
								<div class="panel">
									<p class="panel-title">Студенческий билет (связь 1:1)</p>
									{#if s.card}
										<div class="card-line">
											<span class="card-number">{s.card.card_number}</span>
											<span class="muted">выдан {fmtDate(s.card.issue_date)}</span>
											<button class="btn btn-sm btn-danger" onclick={() => removeCard(s)}>Удалить билет</button>
										</div>
									{:else}
										<div class="card-line">
											<span class="muted">Билет не выдан</span>
											<button class="btn btn-sm btn-primary" onclick={() => openCard(s)}>Выдать билет</button>
										</div>
									{/if}
								</div>
								<div class="panel">
									<p class="panel-title">Курсы (связь N:M через students_courses)</p>
									<div class="chips">
										{#each s.courses as c (c.course_id)}
											<span class="chip">
												{c.name}
												<button class="chip-x" title="Отписать от курса" onclick={() => unenrollStudent(s, c)}>✕</button>
											</span>
										{:else}
											<span class="muted">Не записан ни на один курс</span>
										{/each}
									</div>
									<div class="enroll-form">
										<select class="input" bind:value={enrollChoice}>
											<option value="">Выберите курс…</option>
											{#each availableCourses(s) as c (c.course_id)}
												<option value={c.course_id}>{c.name}</option>
											{/each}
										</select>
										<button class="btn btn-primary" disabled={!enrollChoice || busy} onclick={() => enrollStudent(s)}>Записать</button>
									</div>
								</div>
							</div>
						</td>
					</tr>
				{/if}
			{:else}
				<tr>
					<td colspan="8" class="empty">{loading ? 'Загрузка…' : 'Студенты не найдены'}</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>

<div class="pagination">
	<span class="muted">
		{#if total > 0}
			Показано {page * LIMIT + 1}–{Math.min((page + 1) * LIMIT, total)} из {total}
		{:else}
			Ничего не найдено
		{/if}
	</span>
	<div class="pagination-buttons">
		<button class="btn btn-sm" disabled={page === 0 || loading} onclick={() => (page -= 1)}>← Назад</button>
		<span class="muted">стр. {page + 1} / {Math.max(1, Math.ceil(total / LIMIT))}</span>
		<button class="btn btn-sm" disabled={(page + 1) * LIMIT >= total || loading} onclick={() => (page += 1)}>Вперёд →</button>
	</div>
</div>

<Modal
	title={form?.id ? 'Изменить студента' : 'Новый студент'}
	open={form !== null}
	onclose={() => (form = null)}
>
	<form class="form" onsubmit={saveStudent}>
		<label>
			Имя
			<input class="input" required maxlength="100" bind:value={form.name} />
		</label>
		<label>
			Email
			<input class="input" type="email" required maxlength="100" bind:value={form.email} />
		</label>
		<label>
			Возраст (CHECK: ≥ 16)
			<input class="input" type="number" min="16" max="120" required bind:value={form.age} />
		</label>
		<label>
			Группа
			<select class="input" bind:value={form.group_id}>
				<option value="">Без группы</option>
				{#each groups as g (g.group_id)}
					<option value={g.group_id}>{g.name}</option>
				{/each}
			</select>
		</label>
		<div class="form-actions">
			<button class="btn btn-primary" type="submit" disabled={busy}>Сохранить</button>
			<button class="btn" type="button" onclick={() => (form = null)}>Отмена</button>
		</div>
	</form>
</Modal>

<Modal title="Выдать студенческий билет" open={cardFor !== null} onclose={() => (cardFor = null)}>
	<form class="form" onsubmit={saveCard}>
		<p class="muted" style="margin: 0">Студент: {cardFor?.name}</p>
		<label>
			Номер билета (unique)
			<input class="input" required maxlength="20" bind:value={cardNumber} />
		</label>
		<div class="form-actions">
			<button class="btn btn-primary" type="submit" disabled={busy}>Выдать</button>
			<button class="btn" type="button" onclick={() => (cardFor = null)}>Отмена</button>
		</div>
	</form>
</Modal>