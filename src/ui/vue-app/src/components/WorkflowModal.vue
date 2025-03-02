<template>
  <div v-if="show" class="workflow-modal-overlay">
    <div class="workflow-modal">
      <div class="workflow-modal-header">
        <h2>Select Workflow</h2>
        <button class="close-button" @click="close">×</button>
      </div>
      <div class="workflow-modal-body">
        <div v-if="loading" class="loading">
          Loading workflows...
        </div>
        <div v-else-if="error" class="error">
          {{ error }}
        </div>
        <div v-else-if="workflows.length === 0" class="no-workflows">
          No workflows found.
        </div>
        <div v-else class="workflow-list">
          <div 
            v-for="workflow in workflows" 
            :key="workflow.filename"
            class="workflow-item"
            :class="{ selected: selectedWorkflow === workflow.filename }"
            @click="selectWorkflow(workflow.filename)"
          >
            <div class="workflow-name">{{ workflow.name }}</div>
            <div class="workflow-description">{{ workflow.description || 'No description' }}</div>
          </div>
        </div>
      </div>
      <div class="workflow-modal-footer">
        <button 
          class="load-button" 
          :disabled="!selectedWorkflow" 
          @click="loadWorkflow"
        >
          Load
        </button>
        <button class="cancel-button" @click="close">Cancel</button>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'WorkflowModal',
  props: {
    show: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      workflows: [],
      loading: false,
      error: null,
      selectedWorkflow: null
    };
  },
  watch: {
    show(newVal) {
      if (newVal) {
        this.fetchWorkflows();
      } else {
        this.selectedWorkflow = null;
      }
    }
  },
  methods: {
    async fetchWorkflows() {
      this.loading = true;
      this.error = null;
      
      try {
        const response = await axios.get('http://localhost:8000/workflows');
        this.workflows = response.data;
      } catch (error) {
        console.error('Error fetching workflows:', error);
        this.error = 'Failed to load workflows. Please try again.';
      } finally {
        this.loading = false;
      }
    },
    selectWorkflow(filename) {
      this.selectedWorkflow = filename;
    },
    async loadWorkflow() {
      if (!this.selectedWorkflow) return;
      
      try {
        const response = await axios.get(`http://localhost:8000/workflows/${this.selectedWorkflow}`);
        this.$emit('load-workflow', response.data);
        this.close();
      } catch (error) {
        console.error('Error loading workflow:', error);
        this.error = 'Failed to load the selected workflow. Please try again.';
      }
    },
    close() {
      this.$emit('close');
    }
  }
};
</script>

<style scoped>
.workflow-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.workflow-modal {
  background-color: white;
  border-radius: 5px;
  width: 80%;
  max-width: 600px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

.workflow-modal-header {
  padding: 15px 20px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.workflow-modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
}

.close-button {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
}

.workflow-modal-body {
  padding: 20px;
  overflow-y: auto;
  flex-grow: 1;
}

.workflow-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.workflow-item {
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.workflow-item:hover {
  background-color: #f5f5f5;
}

.workflow-item.selected {
  background-color: #e6f7ff;
  border-color: #1890ff;
}

.workflow-name {
  font-weight: bold;
  margin-bottom: 5px;
}

.workflow-description {
  color: #666;
  font-size: 0.9rem;
}

.loading, .error, .no-workflows {
  padding: 20px;
  text-align: center;
  color: #666;
}

.error {
  color: #f5222d;
}

.workflow-modal-footer {
  padding: 15px 20px;
  border-top: 1px solid #eee;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.load-button, .cancel-button {
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.load-button {
  background-color: #1890ff;
  color: white;
  border: none;
}

.load-button:disabled {
  background-color: #d9d9d9;
  cursor: not-allowed;
}

.cancel-button {
  background-color: white;
  color: #666;
  border: 1px solid #d9d9d9;
}
</style>
