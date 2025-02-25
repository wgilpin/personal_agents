<script>
  import { createEventDispatcher } from 'svelte';
  
  export let id;
  export let type;
  export let x = 100;
  export let y = 100;
  export let width = 150;
  export let height = 80;
  export let selected = false;
  export let connections = [];
  
  const dispatch = createEventDispatcher();
  
  let isDragging = false;
  let dragStartX;
  let dragStartY;
  let startX;
  let startY;
  
  function handleMouseDown(event) {
    isDragging = true;
    dragStartX = event.clientX;
    dragStartY = event.clientY;
    startX = x;
    startY = y;
    
    dispatch('select', { id });
    
    // Prevent default to avoid text selection during drag
    event.preventDefault();
  }
  
  function handleMouseMove(event) {
    if (!isDragging) return;
    
    const dx = event.clientX - dragStartX;
    const dy = event.clientY - dragStartY;
    
    x = startX + dx;
    y = startY + dy;
    
    dispatch('move', { id, x, y });
  }
  
  function handleMouseUp() {
    isDragging = false;
  }
  
  function handleConnectionStart(event) {
    // Calculate the center of the node
    const centerX = x + width / 2;
    const centerY = y + height / 2;
    
    // Dispatch the event with the node's ID and center coordinates
    dispatch('connectionStart', { 
      id, 
      x: centerX, 
      y: centerY 
    });
    
    console.log(`Connection point clicked on node ${id} at (${centerX}, ${centerY})`);
    
    // Stop propagation to prevent the node drag behavior
    event.stopPropagation();
    event.preventDefault();
    isDragging = false;
  }
</script>

<svelte:window on:mousemove={handleMouseMove} on:mouseup={handleMouseUp} />

<div 
  class="node {type} {selected ? 'selected' : ''}"
  style="left: {x}px; top: {y}px; width: {width}px; height: {height}px;"
  on:mousedown={handleMouseDown}
>
  <div class="node-header">
    <slot name="header">{type.toUpperCase()}</slot>
  </div>
  <div class="node-content">
    <slot></slot>
  </div>
  <div class="connection-point" on:mousedown={handleConnectionStart} title="Click to start/end a connection">
    <span class="connection-icon">+</span>
    <span class="tooltip">Connect</span>
  </div>
</div>

<style>
  .node {
    position: absolute;
    border-radius: 8px;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
    background-color: white;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    user-select: none;
    cursor: move;
  }
  
  .node.selected {
    box-shadow: 0 0 0 2px #3498db;
  }
  
  .node-header {
    padding: 8px;
    font-weight: bold;
    text-align: center;
    border-bottom: 1px solid #eee;
  }
  
  .node-content {
    flex: 1;
    padding: 8px;
    overflow: auto;
  }
  
  .connection-point {
    position: absolute;
    bottom: -15px;
    right: -15px;
    width: 30px;
    height: 30px;
    background-color: #3498db;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: bold;
    font-size: 18px;
    cursor: pointer;
    z-index: 10;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.3);
    transition: transform 0.2s, background-color 0.2s;
  }
  
  .connection-point:hover {
    transform: scale(1.1);
    background-color: #2980b9;
  }
  
  .connection-point .tooltip {
    position: absolute;
    bottom: 40px;
    right: -10px;
    background-color: rgba(0, 0, 0, 0.7);
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: normal;
    white-space: nowrap;
    opacity: 0;
    transition: opacity 0.2s;
    pointer-events: none;
  }
  
  .connection-point:hover .tooltip {
    opacity: 1;
  }
  
  .act {
    border: 2px solid #2ecc71;
  }
  
  .act .node-header {
    background-color: #2ecc71;
    color: white;
  }
  
  .choice {
    border: 2px solid #f39c12;
  }
  
  .choice .node-header {
    background-color: #f39c12;
    color: white;
  }
  
  .terminal {
    border: 2px solid #e74c3c;
  }
  
  .terminal .node-header {
    background-color: #e74c3c;
    color: white;
  }
</style>
