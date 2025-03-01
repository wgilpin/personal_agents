<template>
  <div 
    :id="node.id" 
    class="node" 
    :class="`node-${node.type}`" 
    :style="{ left: `${node.x}px`, top: `${node.y}px` }"
    @mousedown="handleNodeMouseDown"
  >
    <div class="node-header">
      <div class="node-title">{{ getNodeTitle(node.type) }}</div>
      <button class="node-delete" @click.stop="$emit('delete-node', node.id)">×</button>
    </div>
    <div class="node-content">
      <div 
        class="node-text" 
        contenteditable="true" 
        @input="updateNodeContent($event)"
        @mousedown.stop
        v-text="node.content"
      ></div>
      <div v-if="node.type === 'act'" class="prompt-container">
        <label :for="`${node.id}-prompt`">Command:</label>
        <textarea 
          :id="`${node.id}-prompt`" 
          class="node-prompt" 
          placeholder="Enter command here..."
          @input="updateNodePrompt($event)"
          @mousedown.stop
          v-text="node.prompt"
        ></textarea>
      </div>
    </div>
    
    <!-- Connection points -->
    <div 
      v-for="position in ['top', 'right', 'bottom', 'left']" 
      :key="position"
      class="connection-point" 
      :class="`connection-point-${position}`"
      :data-position="position"
      :data-node-id="node.id"
      @mousedown.stop="$emit('connection-start', node.id, position, $event)"
    ></div>
  </div>
</template>

<script>
export default {
  name: 'FlowchartNode',
  props: {
    node: {
      type: Object,
      required: true
    }
  },
  emits: [
    'delete-node', 
    'update-node', 
    'node-drag-start', 
    'connection-start'
  ],
  methods: {
    getNodeTitle(type) {
      switch (type) {
        case 'act': return 'Action';
        case 'choice': return 'Choice';
        case 'terminal': return 'Terminal';
        default: return 'Node';
      }
    },
    handleNodeMouseDown(e) {
      // Don't start dragging if clicking on connection point or delete button
      if (e.target.classList.contains('connection-point') || 
          e.target.classList.contains('node-delete')) {
        return;
      }
      
      // Emit event to start dragging
      this.$emit('node-drag-start', this.node.id, e);
    },
    updateNodeContent(e) {
      this.$emit('update-node', this.node.id, { content: e.target.textContent });
    },
    updateNodePrompt(e) {
      this.$emit('update-node', this.node.id, { prompt: e.target.value });
    }
  }
};
</script>

<style scoped>
/* Node-specific styles can be added here if needed */
</style>
