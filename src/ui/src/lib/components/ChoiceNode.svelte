<script>
  import Node from './Node.svelte';
  
  export let id;
  export let x = 100;
  export let y = 100;
  export let selected = false;
  export let connections = [];
  export let question = 'Decision?';
  export let options = ['Yes', 'No'];
</script>

<Node 
  {id}
  type="choice"
  {x}
  {y}
  {selected}
  {connections}
  on:select
  on:move
  on:connectionStart
>
  <svelte:fragment slot="header">CHOICE</svelte:fragment>
  <div class="content">
    <input bind:value={question} placeholder="Enter decision question..." />
    <div class="options">
      {#each options as option, i}
        <div class="option">
          <input 
            bind:value={options[i]} 
            placeholder="Option {i+1}" 
          />
          {#if options.length > 2}
            <button on:click={() => options = options.filter((_, index) => index !== i)}>×</button>
          {/if}
        </div>
      {/each}
      {#if options.length < 5}
        <button class="add-option" on:click={() => options = [...options, `Option ${options.length + 1}`]}>
          + Add Option
        </button>
      {/if}
    </div>
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
    margin-bottom: 8px;
  }
  
  .options {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  
  .option {
    display: flex;
    align-items: center;
  }
  
  .option input {
    flex: 1;
    margin-bottom: 0;
  }
  
  .option button {
    background: none;
    border: none;
    color: #e74c3c;
    font-size: 16px;
    cursor: pointer;
    padding: 0 4px;
  }
  
  .add-option {
    background-color: #f39c12;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 4px 8px;
    margin-top: 4px;
    cursor: pointer;
    font-size: 12px;
  }
  
  .add-option:hover {
    background-color: #e67e22;
  }
</style>
