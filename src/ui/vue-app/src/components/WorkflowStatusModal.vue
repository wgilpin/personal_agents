<template>
  <div v-if="show" class="workflow-status-modal">
    <div class="modal-content">
      <span class="close-button" @click="$emit('close')">&times;</span>
      <div class="modal-body">
        <p>{{ message }}</p>
        <div v-if="!isError" class="loading-animation">
          <!-- Add loading animation here -->
          <div class="spinner"></div>
        </div>
        <div v-else class="error-icon">
          <!-- Add error icon here -->
          <i class="material-icons">error</i>
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
    message: String,
    isError: Boolean
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
</style>