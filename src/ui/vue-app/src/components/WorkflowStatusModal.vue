<template>
  <div v-if="show" class="workflow-status-modal">
    <div class="modal-content">
      <span class="close-button" @click="$emit('close')">&times;</span>
      <div class="modal-body">
        <h3 class="modal-title">{{ title }}</h3>
        <p>{{ message }}</p>
        <div v-if="isLoading" class="loading-animation">
          <!-- Loading animation -->
          <div class="spinner"></div>
        </div>
        <div v-else-if="isError" class="error-icon">
          <!-- Error icon -->
          <i class="material-icons">error</i>
        </div>
        <div class="modal-footer">
          <button class="close-btn" @click="$emit('close')">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'WorkflowStatusModal',
  props: {
    show: Boolean,
    title: {
      type: String,
      default: 'Workflow Status'
    },
    message: String,
    isError: Boolean,
    isLoading: {
      type: Boolean,
      default: true
    }
  },
  emits: ['close']
};
</script>

<style scoped>
.workflow-status-modal {
  position: fixed;
  z-index: 1000; /* Increased z-index to be on top */
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  overflow: auto;
  background-color: rgba(0,0,0,0.4);
  display: flex;
  justify-content: center;
  align-items: center;
}

.modal-content {
  background-color: #fefefe;
  margin: 15% auto;
  padding: 20px;
  border: 1px solid #888;
  width: 80%;
  border-radius: 5px;
}

.close-button {
  color: #aaa;
  float: right;
  font-size: 28px;
  font-weight: bold;
}

.close-button:hover,
.close-button:focus {
  color: black;
  text-decoration: none;
  cursor: pointer;
}

.modal-body {
  padding: 20px;
}

.modal-title {
  margin-top: 0;
  margin-bottom: 15px;
  color: #333;
  font-size: 1.5em;
  font-weight: bold;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
}

.loading-animation {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.spinner {
  border: 4px solid rgba(0, 0, 0, 0.1);
  border-left-color: #4CAF50;
  border-radius: 50%;
  width: 30px;
  height: 30px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-icon {
  display: flex;
  justify-content: center;
  margin-top: 20px;
  color: red;
  font-size: 40px;
}

.modal-footer {
  display: flex;
  justify-content: center;
  margin-top: 30px;
}

.close-btn {
  background-color: #4CAF50;
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  transition: background-color 0.3s;
}

.close-btn:hover {
  background-color: #45a049;
}
</style>