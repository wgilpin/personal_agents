<script>
  import { onMount } from 'svelte';
  import { v4 as uuidv4 } from 'uuid';
  import ActNode from './ActNode.svelte';
  import ChoiceNode from './ChoiceNode.svelte';
  import TerminalNode from './TerminalNode.svelte';
  import Connection from './Connection.svelte';
  
  // Flowchart data
  export let nodes = [];
  export let connections = [];
  
  // State variables
  let selectedNodeId = null;
  let selectedConnectionId = null;
  let isCreatingConnection = false;
  let connectionStartNodeId = null;
  let connectionStartX = 0;
  let connectionStartY = 0;
  let connectionEndX = 0;
  let connectionEndY = 0;
  let nextNodeId = 1;
  
  // Handle node selection
  function handleNodeSelect(event) {
    const { id } = event.detail;
    
    // If we're in connection creation mode, handle connecting to this node
    if (isCreatingConnection && connectionStartNodeId && connectionStartNodeId !== id) {
      createConnection(connectionStartNodeId, id);
      return;
    }
    
    selectedNodeId = id;
    selectedConnectionId = null;
  }
  
  // Handle connection selection
  function handleConnectionSelect(event) {
    const { id } = event.detail;
    selectedConnectionId = id;
    selectedNodeId = null;
  }
  
  // Handle connection label change
  function handleConnectionLabelChange(event) {
    const { id, label } = event.detail;
    connections = connections.map(conn => 
      conn.id === id ? { ...conn, label } : conn
    );
  }
  
  // Handle node movement
  function handleNodeMove(event) {
    const { id, x, y } = event.detail;
    
    // Update connections when nodes move
    connections = connections.map(conn => {
      if (conn.from === id) {
        return {
          ...conn,
          startX: x + 75, // Half of node width
          startY: y + 40, // Half of node height
        };
      }
      if (conn.to === id) {
        return {
          ...conn,
          endX: x + 75, // Half of node width
          endY: y + 40, // Half of node height
        };
      }
      return conn;
    });
  }
  
  // Handle connection start
  function handleConnectionStart(event) {
    const { id, x, y } = event.detail;
    
    // Start connection mode
    isCreatingConnection = true;
    connectionStartNodeId = id;
    
    // Set the start coordinates
    connectionStartX = x;
    connectionStartY = y;
    connectionEndX = x;
    connectionEndY = y;
    
    console.log("Connection started from node:", id, "at", x, y);
    
    // Prevent the event from being treated as a node drag
    event.stopPropagation();
    selectedNodeId = null;
  }
  
  // Create a connection between two nodes
  function createConnection(fromNodeId, toNodeId) {
    const sourceNode = nodes.find(node => node.id === fromNodeId);
    const targetNode = nodes.find(node => node.id === toNodeId);
    
    if (sourceNode && targetNode) {
      const newConnection = {
        id: uuidv4(),
        from: fromNodeId,
        to: toNodeId,
        startX: sourceNode.x + 75, // Half of node width
        startY: sourceNode.y + 40, // Half of node height
        endX: targetNode.x + 75, // Half of node width
        endY: targetNode.y + 40, // Half of node height
        label: ''
      };
      
      connections = [...connections, newConnection];
      console.log("Connection created:", newConnection);
    }
    
    // Exit connection mode
    isCreatingConnection = false;
    connectionStartNodeId = null;
  }
  
  // Handle mouse move during connection creation
  function handleMouseMove(event) {
    if (!isCreatingConnection) return;
    
    const rect = event.currentTarget.getBoundingClientRect();
    connectionEndX = event.clientX - rect.left;
    connectionEndY = event.clientY - rect.top;
  }
  
  // Handle mouse up during connection creation - for canceling
  function handleMouseUp(event) {
    // If clicked on empty space while in connection mode, cancel the connection
    if (isCreatingConnection) {
      const rect = event.currentTarget.getBoundingClientRect();
      const mouseX = event.clientX - rect.left;
      const mouseY = event.clientY - rect.top;
      
      // Check if we clicked on a node
      const clickedOnNode = nodes.some(node => {
        const nodeLeft = node.x - 20;
        const nodeRight = node.x + 170; // Node width + padding
        const nodeTop = node.y - 20;
        const nodeBottom = node.y + 100; // Node height + padding
        
        return mouseX >= nodeLeft && mouseX <= nodeRight && mouseY >= nodeTop && mouseY <= nodeBottom;
      });
      
      // If we didn't click on a node, cancel the connection
      if (!clickedOnNode) {
        isCreatingConnection = false;
        connectionStartNodeId = null;
      }
    }
  }
  
  // Add a new node
  function addNode(type) {
    const id = `node-${nextNodeId++}`;
    const x = 100 + Math.random() * 300;
    const y = 100 + Math.random() * 200;
    
    const newNode = { id, type, x, y };
    nodes = [...nodes, newNode];
    selectedNodeId = id;
  }
  
  // Delete selected node or connection
  function deleteSelected() {
    if (selectedNodeId) {
      nodes = nodes.filter(node => node.id !== selectedNodeId);
      connections = connections.filter(conn => conn.from !== selectedNodeId && conn.to !== selectedNodeId);
      selectedNodeId = null;
    } else if (selectedConnectionId) {
      connections = connections.filter(conn => conn.id !== selectedConnectionId);
      selectedConnectionId = null;
    }
  }
  
  // Clear the flowchart
  function clearFlowchart() {
    if (confirm('Are you sure you want to clear the flowchart?')) {
      nodes = [];
      connections = [];
      selectedNodeId = null;
      selectedConnectionId = null;
      nextNodeId = 1;
    }
  }
  
  // Handle keyboard shortcuts
  function handleKeyDown(event) {
    if (event.key === 'Delete' || event.key === 'Backspace') {
      deleteSelected();
    }
  }
  
  onMount(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  });
</script>

<div class="flowchart-container {isCreatingConnection ? 'connection-mode' : ''}">
  <div class="toolbar">
    <div class="node-buttons">
      <button on:click={() => addNode('act')}>Add Action</button>
      <button on:click={() => addNode('choice')}>Add Choice</button>
      <button on:click={() => addNode('terminal')}>Add Terminal</button>
    </div>
    <div class="control-buttons">
      <button on:click={deleteSelected} disabled={!selectedNodeId && !selectedConnectionId}>Delete Selected</button>
      <button on:click={clearFlowchart}>New Flowchart</button>
    </div>
  </div>
  
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="flowchart-canvas" on:mousemove={handleMouseMove} on:mouseup={handleMouseUp}>
    <svg class="connections-layer" width="100%" height="100%">
      {#each connections as connection}
        <Connection 
          id={connection.id}
          startX={connection.startX}
          startY={connection.startY}
          endX={connection.endX}
          endY={connection.endY}
          selected={selectedConnectionId === connection.id}
          label={connection.label}
          on:select={handleConnectionSelect}
          on:labelChange={handleConnectionLabelChange}
        />
      {/each}
      
      {#if isCreatingConnection}
        <!-- Connection guide line -->
        <path 
          d="M {connectionStartX} {connectionStartY} L {connectionEndX} {connectionEndY}" 
          stroke="#3498db" 
          stroke-width="3" 
          stroke-dasharray="5,5" 
          fill="none" 
        />
        
        <!-- Start point indicator -->
        <circle 
          cx={connectionStartX} 
          cy={connectionStartY} 
          r="6" 
          fill="#3498db" 
        />
        
        <!-- End point indicator -->
        <circle 
          cx={connectionEndX} 
          cy={connectionEndY} 
          r="6" 
          fill="#3498db" 
        />
      {/if}
    </svg>
    
    <div class="nodes-layer">
      {#each nodes as node (node.id)}
        {#if node.type === 'act'}
          <ActNode 
            id={node.id}
            x={node.x}
            y={node.y}
            selected={selectedNodeId === node.id}
            connections={connections.filter(c => c.from === node.id || c.to === node.id)}
            on:select={handleNodeSelect}
            on:move={handleNodeMove}
            on:connectionStart={handleConnectionStart}
          />
        {:else if node.type === 'choice'}
          <ChoiceNode 
            id={node.id}
            x={node.x}
            y={node.y}
            selected={selectedNodeId === node.id}
            connections={connections.filter(c => c.from === node.id || c.to === node.id)}
            on:select={handleNodeSelect}
            on:move={handleNodeMove}
            on:connectionStart={handleConnectionStart}
          />
        {:else if node.type === 'terminal'}
          <TerminalNode 
            id={node.id}
            x={node.x}
            y={node.y}
            selected={selectedNodeId === node.id}
            connections={connections.filter(c => c.from === node.id || c.to === node.id)}
            on:select={handleNodeSelect}
            on:move={handleNodeMove}
            on:connectionStart={handleConnectionStart}
          />
        {/if}
      {/each}
    </div>
  </div>
</div>

<style>
  .flowchart-container {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    overflow: hidden;
    position: relative;
  }
  
  .flowchart-container.connection-mode::after {
    content: "Connection Mode: Click on another node to connect";
    position: absolute;
    top: 60px;
    left: 50%;
    transform: translateX(-50%);
    background-color: rgba(52, 152, 219, 0.9);
    color: white;
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 14px;
    z-index: 100;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
  }
  
  .toolbar {
    display: flex;
    justify-content: space-between;
    padding: 10px;
    background-color: #f5f5f5;
    border-bottom: 1px solid #ddd;
  }
  
  .node-buttons, .control-buttons {
    display: flex;
    gap: 10px;
  }
  
  button {
    padding: 8px 12px;
    border: none;
    border-radius: 4px;
    background-color: #3498db;
    color: white;
    cursor: pointer;
    font-size: 14px;
  }
  
  button:hover {
    background-color: #2980b9;
  }
  
  button:disabled {
    background-color: #bdc3c7;
    cursor: not-allowed;
  }
  
  .flowchart-canvas {
    position: relative;
    flex: 1;
    overflow: auto;
    background-color: #f9f9f9;
    background-image: 
      linear-gradient(rgba(0, 0, 0, 0.1) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0, 0, 0, 0.1) 1px, transparent 1px);
    background-size: 20px 20px;
  }
  
  .connections-layer {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
  }
  
  .nodes-layer {
    position: relative;
    width: 100%;
    height: 100%;
  }
</style>
