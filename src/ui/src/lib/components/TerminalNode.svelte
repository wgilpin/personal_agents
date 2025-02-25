<script>
  import Node from './Node.svelte';
  
  export let id;
  export let x = 100;
  export let y = 100;
  export let selected = false;
  export let connections = [];
  export let text = 'End';
  export let type = 'success'; // success, failure, neutral
</script>

<Node 
  {id}
  type="terminal"
  {x}
  {y}
  {selected}
  {connections}
  on:select
  on:move
  on:connectionStart
>
  <svelte:fragment slot="header">TERMINAL</svelte:fragment>
  <div class="content">
    <input bind:value={text} placeholder="Enter terminal state..." />
    <div class="type-selector">
      <label>
        <input type="radio" bind:group={type} value="success" />
        Success
      </label>
      <label>
        <input type="radio" bind:group={type} value="failure" />
        Failure
      </label>
      <label>
        <input type="radio" bind:group={type} value="neutral" />
        Neutral
      </label>
    </div>
  </div>
</Node>

<style>
  .content {
    display: flex;
    flex-direction: column;
    height: 100%;
  }
  
  input[type="text"] {
    width: 100%;
    padding: 4px;
    border: 1px solid #ddd;
    border-radius: 4px;
    margin-bottom: 8px;
  }
  
  .type-selector {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  
  label {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
  }
</style>
