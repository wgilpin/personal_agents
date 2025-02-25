<script>
  import { createEventDispatcher } from 'svelte';
  
  export let id;
  export let startX;
  export let startY;
  export let endX;
  export let endY;
  export let selected = false;
  export let label = '';
  
  const dispatch = createEventDispatcher();
  
  let isEditingLabel = false;
  
  // Calculate the path for the arrow
  $: path = `M ${startX} ${startY} C ${startX + (endX - startX) / 2} ${startY}, ${startX + (endX - startX) / 2} ${endY}, ${endX} ${endY}`;
  
  // Calculate the position for the label
  $: labelX = startX + (endX - startX) / 2;
  $: labelY = startY + (endY - startY) / 2 - 10;
  
  // Calculate the arrow head position
  $: {
    // Get the point slightly before the end for the arrow head
    const t = 0.95; // Parameter along the curve (0 to 1)
    const x1 = startX + (endX - startX) * t;
    const y1 = startY + (endY - startY) * t;
    
    // Calculate the angle of the line at the end
    const angle = Math.atan2(endY - y1, endX - x1);
    
    // Calculate the arrow head points
    const arrowSize = 10;
    arrowPoint1X = endX - arrowSize * Math.cos(angle - Math.PI / 6);
    arrowPoint1Y = endY - arrowSize * Math.sin(angle - Math.PI / 6);
    arrowPoint2X = endX - arrowSize * Math.cos(angle + Math.PI / 6);
    arrowPoint2Y = endY - arrowSize * Math.sin(angle + Math.PI / 6);
  }
  
  let arrowPoint1X, arrowPoint1Y, arrowPoint2X, arrowPoint2Y;
  
  function handleClick(event) {
    dispatch('select', { id });
    
    // If clicking on the label area, start editing
    const rect = event.target.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const clickY = event.clientY - rect.top;
    
    const distToLabel = Math.sqrt(
      Math.pow(clickX - labelX, 2) + Math.pow(clickY - labelY, 2)
    );
    
    if (distToLabel < 40) {
      isEditingLabel = true;
    }
    
    event.stopPropagation();
  }
  
  function handleLabelChange(event) {
    label = event.target.value;
    dispatch('labelChange', { id, label });
  }
  
  function handleLabelBlur() {
    isEditingLabel = false;
  }
  
  function handleLabelKeyDown(event) {
    if (event.key === 'Enter') {
      isEditingLabel = false;
    }
  }
</script>

<g class="connection {selected ? 'selected' : ''}" on:click={handleClick} style="pointer-events: all; cursor: pointer;">
  <!-- Main connection path -->
  <path d={path} class="connection-path" />
  
  <!-- Arrow head -->
  <path d="M {endX} {endY} L {arrowPoint1X} {arrowPoint1Y} L {arrowPoint2X} {arrowPoint2Y} Z" class="arrow-head" />
  
  <!-- Connection label -->
  <g class="label-container" transform="translate({labelX}, {labelY})">
    {#if isEditingLabel}
      <foreignObject x="-60" y="-15" width="120" height="30">
        <input 
          type="text" 
          bind:value={label} 
          on:change={handleLabelChange}
          on:blur={handleLabelBlur}
          on:keydown={handleLabelKeyDown}
          class="label-input"
          placeholder="Add label..."
          autofocus
        />
      </foreignObject>
    {:else}
      <rect x="-60" y="-15" width="120" height="30" rx="5" ry="5" class="label-bg" />
      <text x="0" y="0" text-anchor="middle" dominant-baseline="middle" class="label-text">
        {label || 'Click to add label'}
      </text>
    {/if}
  </g>
</g>

<style>
  .connection-path {
    fill: none;
    stroke: #666;
    stroke-width: 2;
    stroke-dasharray: none;
    cursor: pointer;
    pointer-events: stroke;
  }
  
  .arrow-head {
    fill: #666;
    stroke: none;
    cursor: pointer;
  }
  
  .connection.selected .connection-path,
  .connection.selected .arrow-head {
    stroke: #3498db;
    fill: #3498db;
  }
  
  .label-bg {
    fill: white;
    stroke: #ddd;
    stroke-width: 1;
    cursor: pointer;
    opacity: 0.8;
  }
  
  .connection.selected .label-bg {
    stroke: #3498db;
    stroke-width: 2;
  }
  
  .label-text {
    font-size: 12px;
    fill: #333;
    cursor: pointer;
    user-select: none;
  }
  
  .connection:hover .label-bg {
    fill: #f5f5f5;
  }
  
  .label-input {
    width: 100%;
    height: 100%;
    border: 2px solid #3498db;
    border-radius: 5px;
    padding: 2px 5px;
    font-size: 12px;
    text-align: center;
    outline: none;
  }
</style>
