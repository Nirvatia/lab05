<script>
	let { title, open = false, onclose, children } = $props();

	let dialogEl = $state(null);

	$effect(() => {
		if (open && dialogEl) dialogEl.focus();
	});

	function onKeydown(e) {
		if (e.key === 'Escape') onclose();
	}
</script>

{#if open}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="overlay" role="presentation" onclick={onclose} onkeydown={onKeydown}>
		<div
			class="modal"
			role="dialog"
			aria-modal="true"
			aria-label={title}
			tabindex="-1"
			bind:this={dialogEl}
			onclick={(e) => e.stopPropagation()}
			onkeydown={onKeydown}
		>
			<div class="modal-head">
				<h3>{title}</h3>
				<button class="btn btn-ghost" onclick={onclose} aria-label="Закрыть">✕</button>
			</div>
			{@render children()}
		</div>
	</div>
{/if}