<template>
  <div class="app-container">
    <Toolbar @create-node="createNode" @new-workflow="createNewWorkflow" @publish-workflow="publishWorkflow"
      @load-workflow-click="showWorkflowModal = true" @start-workflow-click="startWorkflow" />
    <div class="instructions">
      <p>To create a connection: Click on a connection point (white circle) of one node, then click on a connection
        point of another node.</p>
    </div>
    <div class="canvas-container" :class="{ 'with-execution-pane': currentWorkflowExecution }">
      <FlowchartCanvas ref="canvas" :nodes="nodes" :connections="connections" @update-node="updateNode"
        @delete-node="deleteNode" @create-connection="createConnection" @update-connections="updateConnections" />
    </div>

    <!-- Workflow Execution Info Pane -->
    <div v-if="currentWorkflowExecution" class="workflow-execution-pane">
      <div class="execution-header">
        <h3>Last Execution: {{ formatDate(currentWorkflowExecution.start_time) }}</h3>
        <span :class="['execution-status', currentWorkflowExecution.success ? 'success' : 'failed']">
          {{ currentWorkflowExecution.success ? 'Success' : 'Failed' }}
        </span>
      </div>
      <div class="execution-result">
        <div v-html="formatExecutionResult(currentWorkflowExecution.result)"></div>
      </div>
    </div>

    <WorkflowModal :show="showWorkflowModal" @close="showWorkflowModal = false" @load-workflow="loadWorkflow" />

    <WorkflowStatusModal :show="workflowStatusModalVisible" :title="workflowStatusTitle"
      :message="workflowStatusMessage" :isError="workflowStatusIsError" :isLoading="workflowStatusIsLoading"
      @close="workflowStatusModalVisible = false" />
  </div>
</template>

<script>
import Toolbar from './components/Toolbar.vue';
import FlowchartCanvas from './components/FlowchartCanvas.vue';
import WorkflowModal from './components/WorkflowModal.vue';
import WorkflowStatusModal from './components/WorkflowStatusModal.vue';
import axios from 'axios';
import { marked } from 'marked';

export default {
  name: 'App',
  components: {
    Toolbar,
    FlowchartCanvas,
    WorkflowModal,
    WorkflowStatusModal
  },
  data() {
    return {
      nodes: [],
      connections: [],
      nextNodeId: 1,
      lastNodePosition: { x: 100, y: 100 },
      showWorkflowModal: false,

      currentWorkflowId: null, // Track the current workflow ID
      currentWorkflowName: null, // Track the current workflow name
      workflowStatusModalVisible: false,
      workflowStatusTitle: '',
      workflowStatusMessage: '',
      workflowStatusIsError: false,
      workflowStatusIsLoading: true
      ,
      currentWorkflowExecution: null
    }
  },
  methods: {
    startWorkflow() {
      // DEBUGGING: Place a breakpoint on this line to debug workflow execution
      // Only prompt for a name if the workflow doesn't already have one
      let workflowName = this.currentWorkflowName;
      if (!workflowName) {
        workflowName = prompt('Enter a name for your workflow before running:', 'My Workflow');


        // If the user cancels, return without running
        if (!workflowName) {
          alert('Workflow name is required to run the workflow.');
          return;
        }

        // Store the name for future use
        this.currentWorkflowName = workflowName;
      }

      // Show status modal while saving and running
      this.workflowStatusModalVisible = true
      this.workflowStatusTitle = 'Saving and Running Workflow'
      this.workflowStatusMessage = 'Please wait while the flowchart is saved and executed...'
      this.workflowStatusIsError = false
      this.workflowStatusIsLoading = true

      // Convert workflow to JSON format with the provided name
      const workflowData = this.convertWorkflowToJson(workflowName);

      // Create a Blob with the JSON content
      const blob = new Blob([workflowData], { type: 'application/json' });

      // Create a FormData object to send the file to the server
      const formData = new FormData();
      formData.append('file', blob, 'workflow.json');

      // First save the workflow
      axios.post('http://localhost:8000/workflows', formData)
        .then(() => {
          console.log('Flowchart saved successfully, now executing it directly');

          // Find the first action node in our local nodes to get its prompt
          let nodePrompt = 'Execute workflow'; // Default fallback

          const firstNode = this.nodes.find(node => node.type === 'act')
            ;
          if (firstNode && firstNode.prompt) {
            nodePrompt = firstNode.prompt
              ;
          }

          // Update status message
          this.workflowStatusTitle = 'Workflow Running';
          this.workflowStatusMessage = 'Please wait while the workflow executes...';


          // Generate a workflow ID from the name if we don't have one yet
          if (!this.currentWorkflowId) {
            this.currentWorkflowId = workflowName.replace(/\s+/g, '_');
          }

          // Execute the workflow

          console.log('Executing workflow with prompt:', nodePrompt);
          return axios.post(`http://localhost:8000/workflows/${this.currentWorkflowId}/execute`, {
            input: nodePrompt
          })
            ;
        })
        .then(response => {
          // Extract response_text from the response data
          let responseText = 'Completed';

          // First check if response_text exists directly in response.data
          if (response.data?.response_text) {
            responseText = response.data.response_text;
          }
          // Then check if it's in final_result as a JSON string
          else if (response.data?.final_result) {
            try {
              const finalResult = JSON.parse(response.data.final_result);
              if (finalResult?.response_text) {
                responseText = finalResult.response_text;
              }
            } catch (e) {
              console.error('Error parsing final_result:', e);
              // If final_result is not valid JSON, use it directly as the response text
              if (response.data.final_result) {
                responseText = response.data.final_result;
              }
            }
          }

          this.workflowStatusTitle = 'Workflow Completed Successfully';
          this.workflowStatusMessage = responseText;
          this.workflowStatusIsLoading = false;

          // Fetch execution data to update the pane
          const workflowFilename = this.currentWorkflowId
            ? this.currentWorkflowId
            : null;
          if (workflowFilename) {
            this.fetchWorkflowExecutionData(workflowFilename);
          }
        })
        .catch(error => {
          this.workflowStatusTitle = 'Workflow Failed!';
          this.workflowStatusMessage = error.message;
          this.workflowStatusIsError = true;
          this.workflowStatusIsLoading = false;
        })
        .finally(() => {
          const workflowFilename = this.currentWorkflowId || null;

          if (workflowFilename) {
            this.fetchWorkflowExecutionData(workflowFilename)
          }
        });
    },
    createNode(type, content = '', prompt = '') {
      // Position new node 20px right and 20px down from the last node
      const x = this.lastNodePosition.x + 20;
      const y = this.lastNodePosition.y + 20;

      // Ensure node is within canvas bounds (assuming canvas is at least 800x600)
      const boundedX = Math.max(20, Math.min(780, x));
      const boundedY = Math.max(20, Math.min(580, y));

      const nodeId = `node-${this.nextNodeId++}`;

      const newNode = {
        id: nodeId,
        type,
        x: boundedX,
        y: boundedY,
        content,
        prompt: (type === 'act' || type === 'choice') ? prompt : null
      };

      this.nodes.push(newNode);

      // Update last node position
      this.lastNodePosition = { x: boundedX, y: boundedY };

      return newNode;
    },

    updateNode(nodeId, updates) {
      console.log('updateNode called with nodeId:', nodeId, 'updates:', updates, 'typeof nodeId:', typeof nodeId, 'typeof updates:', typeof updates);
      const nodeIndex = this.nodes.findIndex(n => n.id === nodeId);
      if (nodeIndex !== -1) {
        this.nodes[nodeIndex] = { ...this.nodes[nodeIndex], ...updates };

        // If position was updated, update last node position
        if (updates.x !== undefined && updates.y !== undefined) {
          this.lastNodePosition = { x: updates.x, y: updates.y };
        }
      }
    },

    deleteNode(nodeId) {
      // Remove node
      this.nodes = this.nodes.filter(n => n.id !== nodeId);

      // Remove connections
      this.connections = this.connections.filter(
        c => c.startNodeId !== nodeId && c.endNodeId !== nodeId
      );
    },

    createConnection(startNodeId, startPosition, endNodeId, endPosition) {
      const connectionId = `connection-${startNodeId}-${startPosition}-${endNodeId}-${endPosition}`;

      // Check if connection already exists
      if (this.connections.some(c => c.id === connectionId)) {
        return;
      }

      // Add to connections
      this.connections.push({
        id: connectionId,
        startNodeId,
        startPosition,
        endNodeId,
        endPosition
      });
    },

    updateConnections() {
      // This method is a placeholder for any additional logic needed
      // The actual connection path updates are handled in the FlowchartCanvas component
    },

    createNewWorkflow() {
      // Reset state
      this.nodes = [];
      this.currentWorkflowId = null; // Reset the workflow ID
      this.currentWorkflowName = null; // Reset the workflow name
      this.connections = [];
      this.nextNodeId = 1;
      this.lastNodePosition = { x: 100, y: 100 };
    },

    publishWorkflow() {
      // Prompt the user for a workflow name
      const workflowName = prompt('Enter a name for your workflow:', this.currentWorkflowName || 'My Workflow');

      // If the user cancels, return
      if (!workflowName) {
        alert('Workflow name is required.');
        return;
      }

      // Store the name for future use
      this.currentWorkflowName = workflowName;

      // Convert flowchart to JSON format with the provided name
      const flowchartData = this.convertWorkflowToJson(workflowName);

      // Log the nodes before conversion
      console.log('Nodes before JSON conversion:', JSON.stringify(this.nodes, null, 2));
      console.log('JSON data being sent to API:', flowchartData);

      // Generate a workflow ID from the name
      this.currentWorkflowId = workflowName.replace(/\s+/g, '_');

      // Create a Blob with the JSON content
      const blob = new Blob([flowchartData], { type: 'application/json' });

      // Create a FormData object to send the file to the server
      const formData = new FormData();
      formData.append('file', blob, 'workflow.json');

      // Send the file to the server
      axios.post('http://localhost:8000/workflows', formData)
        .then(response => {
          if (response.data.success) {
            // Show success message
            alert('Flowchart published successfully!');
          } else {
            // Show error message
            alert(`Error publishing flowchart: ${response.data.message}`);
          }
        })
        .catch(error => {
          // Show error message
          alert(`Error publishing flowchart: ${error.message}`);
        });
    },

    convertWorkflowToJson(workflowName) {
      // Create a structured object for the workflow
      const workflow = {
        // Add metadata section
        metadata: {
          name: workflowName || 'Untitled Workflow', // Use provided name or default
        },
        nodes: this.nodes.map(node => {
          // Create a clean node object
          const cleanNode = {
            id: node.id,
            type: node.type,
            position: {
              x: node.x,
              y: node.y
            },
            content: node.content
          };

          // Add prompt for action and choice nodes
          if (node.type === 'act' || node.type === 'choice') {
            cleanNode.prompt = node.prompt || '';
          }

          return cleanNode;
        }),
        connections: this.connections.map(conn => {
          // Create a clean connection object
          return {
            from: {
              nodeId: conn.startNodeId,
              position: conn.startPosition
            },
            to: {
              nodeId: conn.endNodeId,
              position: conn.endPosition
            }
          };
        })
      };

      // Convert to JSON string
      return JSON.stringify(workflow, null, 2);
    },

    loadWorkflow(workflowData) {
      // Generate workflow ID from metadata name or use the ID directly
      const workflowId = workflowData.id || (workflowData.metadata?.name ? workflowData.metadata.name.replace(/\s+/g, '_') : null);
      // Reset the current workflow
      this.createNewWorkflow();

      // Store the workflow name after resetting
      if (workflowData.metadata?.name) {
        this.currentWorkflowName = workflowData.metadata.name;
      }

      // Preserve metadata if it exists
      if (workflowData.metadata) {
        // We don't need to do anything with the metadata here
        // It will be preserved when saving the workflow
      }

      // Store the workflow ID
      this.currentWorkflowId = workflowId;

      // Load the nodes from the workflow data
      if (workflowData.nodes && Array.isArray(workflowData.nodes)) {
        // Find the highest node ID to set nextNodeId correctly
        let highestId = 0;

        workflowData.nodes.forEach(node => {
          // Extract the numeric part of the node ID
          const idMatch = node.id.match(/node-(\d+)/);
          if (idMatch && idMatch[1]) {
            const idNum = parseInt(idMatch[1], 10);
            highestId = Math.max(highestId, idNum);
          }

          // Add the node to the canvas
          this.nodes.push({
            id: node.id,
            type: node.type,
            x: node.position.x,
            y: node.position.y,
            content: node.content || '',
            prompt: node.prompt || null
          });
        });

        // Set the next node ID
        this.nextNodeId = highestId + 1;

        // Update the last node position
        if (workflowData.nodes.length > 0) {
          const lastNode = workflowData.nodes[workflowData.nodes.length - 1];
          this.lastNodePosition = {
            x: lastNode.position.x,
            y: lastNode.position.y
          };
        }
      }

      // Add a longer delay to ensure DOM is fully rendered
      setTimeout(() => {
        console.log('Creating connections after delay');

        // Load the connections from the workflow data
        if (workflowData.connections && Array.isArray(workflowData.connections)) {

          workflowData.connections.forEach(conn => {
            // Get the connection details
            const fromNodeId = conn.from.nodeId;
            let fromPosition = conn.from.position;
            const toNodeId = conn.to.nodeId;
            const toPosition = conn.to.position;

            // Fix for yes/no vs true/false mismatch
            // Convert true/false to yes/no
            if (fromPosition === 'true' || fromPosition === true) fromPosition = 'yes';
            if (fromPosition === 'false' || fromPosition === false) fromPosition = 'no';

            console.log(`Creating connection from ${fromNodeId} (${fromPosition}) to ${toNodeId} (${toPosition})`);

            this.createConnection(
              fromNodeId,
              fromPosition,
              toNodeId,
              toPosition
            );
          });

          // Force a redraw of all connections
          this.$nextTick(() => {
            const canvas = this.$refs.canvas;
            if (canvas && typeof canvas.redrawConnections === 'function') {
              canvas.redrawConnections();
            }
          });
        }

      }, 1000); // Increase delay to 1000ms

      // Fetch execution data for the loaded workflow
      if (workflowId) {
        this.fetchWorkflowExecutionData(workflowId);
      }
    },

    async fetchWorkflowExecutionData(filename) {
      try {
        console.log(`Fetching execution data for ${filename}...`);
        const response = await axios.get(`http://localhost:8000/workflows/${filename}/logs/latest`);
        if (response.data.found) {
          this.currentWorkflowExecution = response.data.log;
          console.log(`Added execution data`);
        } else {
          this.currentWorkflowExecution = null;
        }
      } catch (error) {
        console.error(`Error fetching execution data for ${filename}:`, error.message, error.response?.data);
        this.currentWorkflowExecution = null;
      }
    },

    formatDate(isoDateString) {
      return new Date(isoDateString).toLocaleString();
    },

    formatExecutionResult(result) {
      if (!result) return 'No result available';

      // If result is a string that looks like JSON, try to parse it
      if (typeof result === 'string') {
        try {
          const parsed = JSON.parse(result);

          // If it has a response_text field, return that
          if (parsed.response_text) {
            return marked.parse(parsed.response_text);
          }

          return marked.parse(JSON.stringify(parsed, null, 2));
        } catch (e) {
          return marked.parse(result);
        }
      }
      return result;
    }
  }
};
</script>

<style>
@import '../../../ui/styles.css';

.canvas-container.with-execution-pane {
  margin-right: 300px;
  /* Make space for the execution pane */
}

.workflow-execution-pane {
  position: fixed;
  top: 60px;
  /* Below the toolbar */
  right: 0;
  width: 300px;
  bottom: 0;
  background-color: #f8f9fa;
  border-left: 1px solid #ddd;
  padding: 15px;
  box-shadow: -2px 0 10px rgba(0, 0, 0, 0.1);
  overflow-y: auto;
}

.execution-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.execution-status {
  padding: 4px 8px;
  border-radius: 4px;
  font-weight: bold;
}

.execution-status.success {
  background-color: #e6f7ff;
  color: #1890ff;
}

.execution-status.failed {
  background-color: #fff1f0;
  color: #f5222d;
}

.execution-result {
  padding-left: 2px;
  padding-right: 2px;
  ;
}
</style>
