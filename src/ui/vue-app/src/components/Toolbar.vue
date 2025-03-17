<template>
  <div class="toolbar">
    <h1>Workflow Builder</h1>
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
      <button id="new-workflow" @click="$emit('new-workflow')" title="New Workflow"><i class="material-icons">add_box</i></button>
      <button id="publish-workflow" @click="$emit('publish-workflow')" title="Publish Workflow"><i class="material-icons">save</i></button>
      <button id="start-workflow" @click="$emit('start-workflow-click')" title="Start Workflow"><i class="material-icons">play_arrow</i></button>
  </div>
</div>
</template>

<script>
export default {
  name: 'Toolbar',
  emits: ['create-node', 'new-workflow', 'publish-workflow', 'load-workflow-click', 'start-workflow-click'],
  data () {
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

#new-workflow{
  background-color: #faad14;
  color: white;
  border-color: #faad14;
}

#new-workflow:hover {
  color: #9C27B0; /* New Workflow button hover text color */
  background-color: #d48806;
}

#publish-workflow{
  background-color: #1890ff;
  color: white;
  border-color: #1890ff;
}

#publish-workflow:hover {
  color: #FF9800; /* Publish Workflow button hover text color */
  background-color: #096dd9;
}

#start-workflow {
  background-color: #28a745; /* Bootstrap success color */
  color: white;
  border-color: #28a745;
}

#start-workflow:hover {
  background-color: #218838; /* Darker shade for hover */
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
