<script>
	import { api } from '#lib/api.js';
	import Modal from './Modal.svelte';

	let { onchange = () => {} } = $props();

	let courses = $state([]);
	let loading = $state(false);
	let busy = $state(false);
	let error = $state('');
	let form = $state(null);

	async function load() {
		loading = true;
		try {
			courses = await api.courses();
		} catch (e) {
			error = e.message;
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		load();
	});

	function openCreate() {
		form = { id: null, name: '', price: 0, description: '' };
	}

	function openEdit(c) {
		form = { id: c.course_id, name: c.name, price: c.price, description: c.description ?? '' };
	}

	async function saveCourse(e) {
		e.preventDefault();
		const payload = {
			name: form.name.trim(),
			price: Number(form.price),
			description: form.description.trim() || null
		};
		busy = true;
		error = '';
		try {
			if (form.id) await api.updateCourse(form.id, payload);
			else await api.createCourse(payload);
			form = null;
			await load();
			onchange();
		} catch (err) {
			error = err.message;
		} finally {
			busy = false;
		}
	}

	async function removeCourse(c) {
		if (!confirm(`Удалить курс «${c.name}»? Все записи студентов на него (${c.students_count}) будут удалены.`)) return;
		busy = true;
		error = '';
		try {
			await api.deleteCourse(c.course_id);
			await load();
			onchange();
		} catch (e) {
			error = e.message;
		} finally {
			busy = false;
		}
	}
</script>

<div class="toolbar">
	<span class="muted">Название курса ограничено 20 символами — как в models.py (String(20))</span>
	<button class="btn btn-primary" onclick={openCreate}>+ Добавить курс</button>
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
				<th>Название</th>
				<th>Цена</th>
				<th>Описание</th>
				<th>Студентов</th>
				<th></th>
			</tr>
		</thead>
		<tbody>
			{#each courses as c (c.course_id)}
				<tr>
					<td>{c.course_id}</td>
					<td>{c.name}</td>
					<td class="price">{Number(c.price).toFixed(2)} ₽</td>
					<td class="desc-cell" title={c.description ?? ''}>{c.description ?? '—'}</td>
					<td><span class="badge" class:badge-ok={c.students_count > 0}>{c.students_count}</span></td>
					<td>
						<div class="actions">
							<button class="btn btn-sm" onclick={() => openEdit(c)}>Изменить</button>
							<button class="btn btn-sm btn-danger" onclick={() => removeCourse(c)}>Удалить</button>
						</div>
					</td>
				</tr>
			{:else}
				<tr><td colspan="6" class="empty">{loading ? 'Загрузка…' : 'Курсов пока нет'}</td></tr>
			{/each}
		</tbody>
	</table>
</div>

<Modal title={form?.id ? 'Изменить курс' : 'Новый курс'} open={form !== null} onclose={() => (form = null)}>
	<form class="form" onsubmit={saveCourse}>
		<label>
			Название (до 20 символов, unique)
			<input class="input" required maxlength="20" bind:value={form.name} />
		</label>
		<label>
			Цена, ₽
			<input class="input" type="number" min="0" step="0.01" required bind:value={form.price} />
		</label>
		<label>
			Описание
			<textarea class="input" bind:value={form.description}></textarea>
		</label>
		<div class="form-actions">
			<button class="btn btn-primary" type="submit" disabled={busy}>Сохранить</button>
			<button class="btn" type="button" onclick={() => (form = null)}>Отмена</button>
		</div>
	</form>
</Modal>