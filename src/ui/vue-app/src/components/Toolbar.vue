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
    <div class="toolbar-actions">
      <button id="load-workflow" @click="$emit('load-workflow-click')" title="Load Workflow"><i class="material-icons">file_open</i></button>
      <button id="new-flowchart" @click="$emit('new-flowchart')" title="New Workflow"><i class="material-icons">add_box</i></button>
      <button id="publish-flowchart" @click="$emit('publish-flowchart')" title="Publish Workflow"><i class="material-icons">save</i></button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Toolbar',
  emits: ['create-node', 'new-flowchart', 'publish-flowchart', 'load-workflow-click'],
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
.toolbar {
  display: flex;
  padding: 10px;
  border-bottom: 1px solid #ddd;
}

.node-types {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

.toolbar-actions {
  display: flex;
  gap: 10px;
}

button {
  padding: 8px 12px;
  border: 1px solid #ccc;
  background-color: white;
  color: white;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

button:hover {
  background-color: #f0f0f0;
}

.node-button {
  min-width: 80px;
}

.node-button:hover {
  color: #4CAF50; /* Action button hover text color */
}

.node-button-act {
  border-color: #1890ff;
  color: #1890ff;
}

.node-button-choice {
  border-color: #52c41a;
  color: #52c41a;
}

.node-button-terminal {
  border-color: #f5222d;
  color: #f5222d;
}

#new-flowchart {
  background-color: #faad14;
  color: white;
  border-color: #faad14;
}

#new-flowchart:hover {
  color: #9C27B0; /* New Flowchart button hover text color */
  background-color: #d48806;
}

#publish-flowchart {
  background-color: #1890ff;
  color: white;
  border-color: #1890ff;
}

#publish-flowchart:hover {
  color: #FF9800; /* Publish Flowchart button hover text color */
  background-color: #096dd9;
}

#load-workflow {
  background-color: #722ed1;
  color: white;
  border-color: #722ed1;
}

#load-workflow:hover {
  background-color: #5b21a6;
}
</style>
