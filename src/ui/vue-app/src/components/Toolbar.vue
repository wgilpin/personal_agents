<template>
  <div class="toolbar">
    <h1>Flowchart Builder</h1>
    <div class="node-types">
      <button 
        v-for="nodeType in nodeTypes" 
        :key="nodeType.type" 
        class="node-button" 
        :data-type="nodeType.type"
        :class="{ [`node-button-${nodeType.type}`]: true }"
        @click="createNode(nodeType.type)"
      >
        {{ nodeType.label }}
      </button>
    </div>
    <button id="new-flowchart" @click="$emit('new-flowchart')">New Flowchart</button>
    <button id="publish-flowchart" @click="$emit('publish-flowchart')">Publish</button>
  </div>
</template>

<script>
export default {
  name: 'Toolbar',
  emits: ['create-node', 'new-flowchart', 'publish-flowchart'],
  data() {
    return {
      nodeTypes: [
        { type: 'act', label: 'Action' },
        { type: 'choice', label: 'Choice' },
        { type: 'terminal', label: 'Terminal' }
      ]
    };
  },
  methods: {
    createNode(type) {
      this.$emit('create-node', type);
    }
  }
};
</script>

<style scoped>
/* Toolbar-specific styles can be added here if needed */
</style>
