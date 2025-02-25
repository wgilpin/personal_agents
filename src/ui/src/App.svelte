<script>
  import FlowChart from './lib/components/FlowChart.svelte';
</script>

<main>
  <h1>Flowchart Builder</h1>
  <div class="flowchart-wrapper">
    <FlowChart />
  </div>
</main>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  }
  
  main {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100vh;
    overflow: hidden;
  }
  
  h1 {
    text-align: center;
    margin: 0;
    padding: 16px;
    background-color: #34495e;
    color: white;
  }
  
  .flowchart-wrapper {
    flex: 1;
    overflow: hidden;
  }
</style>
