<template>
  <div class="app-container">
    <Toolbar 
      @create-node="createNode" 
      @new-flowchart="createNewFlowchart" 
      @publish-flowchart="publishFlowchart"
      @load-workflow-click="showWorkflowModal = true"
      @start-workflow-click="startWorkflow"
    />
    <div class="instructions">
      <p>To create a connection: Click on a connection point (white circle) of one node, then click on a connection point of another node.</p>
    </div>
    <div class="canvas-container">
      <FlowchartCanvas 
        ref="canvas"
        :nodes="nodes" 
        :connections="connections"
        @update-node="updateNode"
        @delete-node="deleteNode"
        @create-connection="createConnection"
        @update-connections="updateConnections"
      />
    </div>
    
    <WorkflowModal
      :show="showWorkflowModal"
      @close="showWorkflowModal = false"
      @load-workflow="loadWorkflow"
    />

    <WorkflowStatusModal
      :show="workflowStatusModalVisible"
      :message="workflowStatusMessage"
      :isError="workflowStatusIsError"
      @close="workflowStatusModalVisible = false"
    />
  </div>
</template>

<script>
import Toolbar from './components/Toolbar.vue';
import FlowchartCanvas from './components/FlowchartCanvas.vue';
import WorkflowModal from './components/WorkflowModal.vue';
import WorkflowStatusModal from './components/WorkflowStatusModal.vue';
import axios from 'axios';

export default {
  name: 'App',
  components: {
    Toolbar,
    FlowchartCanvas,
    WorkflowModal,
    WorkflowStatusModal
  },
  data () {
    return {
      nodes: [],
      connections: [],
      nextNodeId: 1,
      lastNodePosition: { x: 100, y: 100 },
      showWorkflowModal: false,
      workflowStatusModalVisible: false,
      workflowStatusMessage: '',
      workflowStatusIsError: false
    }
  },
  methods: {
    startWorkflow () {
      this.workflowStatusModalVisible = true
      this.workflowStatusMessage = 'Workflow running...'
      this.workflowStatusIsError = false

      // Get the current workflow filename from the first workflow in the list
      // In a real application, you would want to get the currently selected workflow
      axios.get('http://localhost:8000/workflows')
        .then(response => {
          if (response.data && response.data.length > 0) {
            const filename = response.data[0].filename
            
            // First get the workflow data to extract the first node's prompt
            return axios.get(`http://localhost:8000/workflows/${filename}`)
              .then(workflowResponse => {
                const workflowData = workflowResponse.data
                
                // Find the first action node (type 'act') to get its prompt
                let nodePrompt = "Execute workflow" // Default fallback
                
                if (workflowData.nodes && Array.isArray(workflowData.nodes)) {
                  // Find the first node in the workflow (usually the start node)
                  const firstNode = workflowData.nodes.find(node => node.type === 'act')
                  
                  if (firstNode && firstNode.prompt) {
                    nodePrompt = firstNode.prompt
                  }
                }
                
                // Now execute the workflow with the node's prompt as input
                return axios.post(`http://localhost:8000/workflows/${filename}/execute`, {
                  input: nodePrompt
                })
              })
          } else {
            throw new Error('No workflows available')
          }
        })
        .then(response => {
          this.workflowStatusMessage = 'Workflow completed successfully!\n' + JSON.stringify(response.data, null, 2)
        })
        .catch(error => {
          this.workflowStatusMessage = 'Workflow failed!\n' + error.message
          this.workflowStatusIsError = true
        })
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
        console.log('Node updated:', JSON.stringify(this.nodes[nodeIndex]));
        
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
    
    createNewFlowchart() {
      // Reset state
      this.nodes = [];
      this.connections = [];
      this.nextNodeId = 1;
      this.lastNodePosition = { x: 100, y: 100 };
    },
    
    publishFlowchart() {
      // Prompt the user for a flowchart name
      const flowchartName = prompt('Enter a name for your flowchart:', 'My Flowchart');
      
      // If the user cancels, return
      if (!flowchartName) {
        alert('Flowchart name is required.');
        return;
      }
      
      // Convert flowchart to YAML format with the provided name
      const flowchartData = this.convertFlowchartToYaml(flowchartName);
      
      // Log the nodes before conversion
      console.log('Nodes before YAML conversion:', JSON.stringify(this.nodes, null, 2));
      console.log('YAML data being sent to API:', flowchartData);
      
      // Create a Blob with the YAML content
      const blob = new Blob([flowchartData], { type: 'text/yaml' });
      
      // Create a FormData object to send the file to the server
      const formData = new FormData();
      formData.append('file', blob, 'flowchart.yaml');
      
      // Send the file to the server
      axios.post('http://localhost:8000/flowchart', formData)
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
    
    convertFlowchartToYaml(flowchartName) {
      // Create a structured object for the flowchart
      const flowchart = {
        // Add metadata section
        metadata: {
          name: flowchartName || 'Untitled Flowchart', // Use provided name or default
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
            console.log(`Node ${node.id} prompt before cleaning:`, node.prompt);
            cleanNode.prompt = node.prompt || '';
            console.log(`Node ${node.id} prompt after cleaning:`, cleanNode.prompt);
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
      
      // Convert to YAML format
      return this.convertToYaml(flowchart);
    },
    
    convertToYaml(obj, indent = 0) {
      let yaml = '';
      const indentStr = ' '.repeat(indent);
      
      if (Array.isArray(obj)) {
        // Handle arrays
        for (const item of obj) {
          yaml += `${indentStr}- ${typeof item === 'object' ? '\n' + this.convertToYaml(item, indent + 2) : item}\n`;
        }
      } else if (typeof obj === 'object' && obj !== null) {
        // Handle objects
        for (const [key, value] of Object.entries(obj)) {
          // Don't skip null values for the prompt field
          if ((key !== 'prompt' && (value === null || value === undefined))) {
            // Skip null or undefined values except for prompt
            continue;
          } else if (key === 'prompt' && (value === null || value === undefined)) {
            // For prompt field, convert null/undefined to empty string
            yaml += `${indentStr}${key}: ''\n`;
          } else if (typeof value === 'object') {
            yaml += `${indentStr}${key}:\n${this.convertToYaml(value, indent + 2)}`;
          } else if (typeof value === 'string' && value.includes('\n')) {
            // Handle multiline strings (like prompts)
            yaml += `${indentStr}${key}: |\n`;
            const lines = value.split('\n');
            for (const line of lines) {
              yaml += `${indentStr}  ${line}\n`;
            }
          } else {
            yaml += `${indentStr}${key}: ${value}\n`;
          }
        }
      }
      
      return yaml;
    },
    
    downloadYamlFile(yamlContent) {
      const downloadLink = document.createElement('a');
      downloadLink.href = URL.createObjectURL(new Blob([yamlContent], { type: 'text/yaml' }));
      downloadLink.download = 'flowchart.yaml';
      downloadLink.click();
    },
    
    loadWorkflow(workflowData) {
      console.log('Loading workflow:', workflowData);
      
      // Reset the current flowchart
      this.createNewFlowchart();
      
      // Preserve metadata if it exists
      if (workflowData.metadata) {
        // We don't need to do anything with the metadata here
        // It will be preserved when saving the workflow
      }
      
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
          console.log('Connections to create:', workflowData.connections);
          
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
    }
  }
};
</script>

<style>
@import '../../../ui/styles.css';
</style>
