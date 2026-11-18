<script>
	import { api } from '#lib/api.js';
	import Modal from './Modal.svelte';

	let { onchange = () => {} } = $props();

	let groups = $state([]);
	let loading = $state(false);
	let busy = $state(false);
	let error = $state('');
	let newName = $state('');
	let editing = $state(null);

	async function load() {
		loading = true;
		try {
			groups = await api.groups();
		} catch (e) {
			error = e.message;
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		load();
	});

	async function addGroup(e) {
		e.preventDefault();
		busy = true;
		error = '';
		try {
			await api.createGroup({ name: newName.trim() });
			newName = '';
			await load();
			onchange();
		} catch (e) {
			error = e.message;
		} finally {
			busy = false;
		}
	}

	async function saveEdit(e) {
		e.preventDefault();
		busy = true;
		error = '';
		try {
			await api.updateGroup(editing.group_id, { name: editing.name.trim() });
			editing = null;
			await load();
			onchange();
		} catch (e) {
			error = e.message;
		} finally {
			busy = false;
		}
	}

	async function removeGroup(g) {
		if (!confirm(`Удалить группу «${g.name}»? Студенты (${g.students_count} чел.) останутся без группы (SET NULL).`)) return;
		busy = true;
		error = '';
		try {
			await api.deleteGroup(g.group_id);
			await load();
			onchange();
		} catch (e) {
			error = e.message;
		} finally {
			busy = false;
		}
	}
</script>

<form class="inline-form" onsubmit={addGroup}>
	<input class="input" placeholder="Название новой группы, например ИВТ-25" required maxlength="50" bind:value={newName} />
	<button class="btn btn-primary" type="submit" disabled={busy || !newName.trim()}>+ Создать группу</button>
</form>

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
				<th>Студентов</th>
				<th></th>
			</tr>
		</thead>
		<tbody>
			{#each groups as g (g.group_id)}
				<tr>
					<td>{g.group_id}</td>
					<td>{g.name}</td>
					<td><span class="badge" class:badge-ok={g.students_count > 0}>{g.students_count}</span></td>
					<td>
						<div class="actions">
							<button class="btn btn-sm" onclick={() => (editing = { group_id: g.group_id, name: g.name })}>Переименовать</button>
							<button class="btn btn-sm btn-danger" onclick={() => removeGroup(g)}>Удалить</button>
						</div>
					</td>
				</tr>
			{:else}
				<tr><td colspan="4" class="empty">{loading ? 'Загрузка…' : 'Групп пока нет'}</td></tr>
			{/each}
		</tbody>
	</table>
</div>

<Modal title="Переименовать группу" open={editing !== null} onclose={() => (editing = null)}>
	<form class="form" onsubmit={saveEdit}>
		<label>
			Название (unique)
			<input class="input" required maxlength="50" bind:value={editing.name} />
		</label>
		<div class="form-actions">
			<button class="btn btn-primary" type="submit" disabled={busy}>Сохранить</button>
			<button class="btn" type="button" onclick={() => (editing = null)}>Отмена</button>
		</div>
	</form>
</Modal>