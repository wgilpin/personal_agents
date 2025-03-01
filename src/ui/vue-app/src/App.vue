<template>
  <div class="app-container">
    <Toolbar 
      @create-node="createNode" 
      @new-flowchart="createNewFlowchart" 
      @publish-flowchart="publishFlowchart" 
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
  </div>
</template>

<script>
import Toolbar from './components/Toolbar.vue';
import FlowchartCanvas from './components/FlowchartCanvas.vue';
import axios from 'axios';

export default {
  name: 'App',
  components: {
    Toolbar,
    FlowchartCanvas
  },
  data() {
    return {
      nodes: [],
      connections: [],
      nextNodeId: 1,
      lastNodePosition: { x: 100, y: 100 }
    };
  },
  methods: {
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
    
    createNewFlowchart() {
      // Reset state
      this.nodes = [];
      this.connections = [];
      this.nextNodeId = 1;
      this.lastNodePosition = { x: 100, y: 100 };
    },
    
    publishFlowchart() {
      // Convert flowchart to YAML format
      const flowchartData = this.convertFlowchartToYaml();
      
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
            
            // Also save a local copy
            this.downloadYamlFile(flowchartData);
          } else {
            // Show error message
            alert(`Error publishing flowchart: ${response.data.message}`);
          }
        })
        .catch(error => {
          // Show error message
          alert(`Error publishing flowchart: ${error.message}`);
          
          // Save a local copy anyway
          this.downloadYamlFile(flowchartData);
        });
    },
    
    convertFlowchartToYaml() {
      // Create a structured object for the flowchart
      const flowchart = {
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
          if ((node.type === 'act' || node.type === 'choice') && node.prompt) {
            cleanNode.prompt = node.prompt;
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
          if (typeof value === 'object' && value !== null) {
            yaml += `${indentStr}${key}:\n${this.convertToYaml(value, indent + 2)}`;
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
    }
  }
};
</script>

<style>
@import '../../../ui/styles.css';
</style>
