<script>
  import Node from './Node.svelte';
  
  export let id;
  export let x = 100;
  export let y = 100;
  export let selected = false;
  export let connections = [];
  export let text = 'Action';
</script>

<Node 
  {id}
  type="act"
  {x}
  {y}
  {selected}
  {connections}
  on:select
  on:move
  on:connectionStart
>
  <svelte:fragment slot="header">ACTION</svelte:fragment>
  <div class="content">
    <input bind:value={text} placeholder="Enter action description..." />
  </div>
</Node>

<style>
  .content {
    display: flex;
    flex-direction: column;
    height: 100%;
  }
  
  input {
    width: 100%;
    padding: 4px;
    border: 1px solid #ddd;
    border-radius: 4px;
  }
</style>
