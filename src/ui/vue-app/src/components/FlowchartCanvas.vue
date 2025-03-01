<template>
  <div id="canvas" ref="canvas" class="canvas" @mousemove="handleCanvasMouseMove" @mouseup="handleCanvasMouseUp">
    <!-- Render all nodes -->
    <FlowchartNode 
      v-for="node in nodes" 
      :key="node.id" 
      :node="node"
      @delete-node="$emit('delete-node', $event)"
      @update-node="$emit('update-node', $event[0], $event[1])"
      @node-drag-start="handleNodeDragStart"
      @connection-start="handleConnectionStart"
    />
    
    <!-- SVG layer for connections -->
    <svg class="connections-layer" ref="connectionsLayer">
      <defs>
        <!-- Define markers for arrowheads -->
        <marker 
          v-for="connection in connections" 
          :key="`arrow-${connection.id}`"
          :id="`arrow-${connection.id}`" 
          viewBox="0 0 10 10" 
          refX="5" 
          refY="5"
          markerWidth="6" 
          markerHeight="6" 
          orient="auto"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#333" />
        </marker>
      </defs>
      
      <!-- Render all connections -->
      <path 
        v-for="connection in connections" 
        :key="connection.id"
        :id="connection.id"
        :d="getConnectionPath(connection)"
        stroke="#333"
        stroke-width="2"
        fill="none"
        :marker-mid="`url(#arrow-${connection.id})`"
      />
      
      <!-- Temporary connection during creation -->
      <g v-if="isConnecting">
        <marker 
          id="temp-arrow" 
          viewBox="0 0 10 10" 
          refX="5" 
          refY="5"
          markerWidth="6" 
          markerHeight="6" 
          orient="auto"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#333" />
        </marker>
        <path 
          id="temp-connection"
          :d="tempConnectionPath"
          stroke="#333"
          stroke-width="2"
          fill="none"
          marker-mid="url(#temp-arrow)"
        />
      </g>
    </svg>
  </div>
</template>

<script>
import FlowchartNode from './FlowchartNode.vue';

export default {
  name: 'FlowchartCanvas',
  components: {
    FlowchartNode
  },
  props: {
    nodes: {
      type: Array,
      required: true
    },
    connections: {
      type: Array,
      required: true
    }
  },
  emits: [
    'update-node', 
    'delete-node', 
    'create-connection', 
    'update-connections'
  ],
  data() {
    return {
      isDragging: false,
      selectedNodeId: null,
      dragOffsetX: 0,
      dragOffsetY: 0,
      isConnecting: false,
      startConnectionNodeId: null,
      startConnectionPosition: null,
      startConnectionPoint: { x: 0, y: 0 },
      tempConnectionPath: '',
      mousePosition: { x: 0, y: 0 }
    };
  },
  mounted() {
    // Add global event listeners for dragging
    document.addEventListener('mousemove', this.handleNodeDrag);
    document.addEventListener('mouseup', this.handleNodeDragEnd);
    
    // Initialize connections layer
    this.$refs.connectionsLayer.setAttribute('width', '100%');
    this.$refs.connectionsLayer.setAttribute('height', '100%');
    this.$refs.connectionsLayer.style.position = 'absolute';
    this.$refs.connectionsLayer.style.top = '0';
    this.$refs.connectionsLayer.style.left = '0';
    this.$refs.connectionsLayer.style.pointerEvents = 'none';
  },
  beforeUnmount() {
    // Remove global event listeners
    document.removeEventListener('mousemove', this.handleNodeDrag);
    document.removeEventListener('mouseup', this.handleNodeDragEnd);
  },
  methods: {
    // Node dragging methods
    handleNodeDragStart(nodeId, event) {
      this.isDragging = true;
      this.selectedNodeId = nodeId;
      
      const node = this.nodes.find(n => n.id === nodeId);
      if (!node) return;
      
      const canvasRect = this.$refs.canvas.getBoundingClientRect();
      
      // Calculate the offset between mouse position and node's current position
      this.dragOffsetX = event.clientX - (canvasRect.left + node.x);
      this.dragOffsetY = event.clientY - (canvasRect.top + node.y);
      
      // Prevent text selection during drag
      event.preventDefault();
    },
    
    handleNodeDrag(event) {
      if (!this.isDragging || !this.selectedNodeId) return;
      
      const canvasRect = this.$refs.canvas.getBoundingClientRect();
      
      // Calculate new position relative to the canvas
      const x = event.clientX - canvasRect.left - this.dragOffsetX;
      const y = event.clientY - canvasRect.top - this.dragOffsetY;
      
      // Update node position
      this.$emit('update-node', this.selectedNodeId, { x, y });
      
      // Update connections
      this.$emit('update-connections', this.selectedNodeId);
    },
    
    handleNodeDragEnd() {
      if (!this.isDragging) return;
      
      // Reset dragging state
      this.isDragging = false;
      this.selectedNodeId = null;
    },
    
    // Connection methods
    handleConnectionStart(nodeId, position, event) {
      event.stopPropagation();
      
      // Get the node type
      const node = this.nodes.find(n => n.id === nodeId);
      if (!node) return;
      
      // If we're already in connecting mode, this is the second click (end point)
      if (this.isConnecting && this.startConnectionNodeId) {
        const endNodeId = nodeId;
        const endPosition = position;
        const endNode = this.nodes.find(n => n.id === endNodeId);
        
        // Don't connect to the same node
        if (endNodeId === this.startConnectionNodeId) {
          // Reset connection state
          this.isConnecting = false;
          this.startConnectionNodeId = null;
          this.startConnectionPosition = null;
          this.tempConnectionPath = '';
          return;
        }
        
        // For terminal nodes, bottom connector can only be used for outgoing connections
        if (endNode && endNode.type === 'terminal' && endPosition === 'bottom') {
          // Reset connection state
          this.isConnecting = false;
          this.startConnectionNodeId = null;
          this.startConnectionPosition = null;
          this.tempConnectionPath = '';
          
          // Reset the highlight on any connection points
          const points = document.querySelectorAll('.connection-point');
          points.forEach(point => {
            point.style.backgroundColor = '#fff';
            point.style.borderColor = '#333';
          });
          
          return;
        }
        
        // Create the connection
        this.$emit('create-connection', 
          this.startConnectionNodeId, 
          this.startConnectionPosition, 
          endNodeId, 
          endPosition
        );
        
        // Reset connection state
        this.isConnecting = false;
        this.startConnectionNodeId = null;
        this.startConnectionPosition = null;
        this.tempConnectionPath = '';
        
        return;
      }
      
      // For choice nodes, only allow connections from yes/no points
      if (node.type === 'choice' && position !== 'yes' && position !== 'no') {
        // Don't allow connections from input points of choice nodes
        return;
      }
      
      // For terminal nodes, enforce connection rules
      if (node.type === 'terminal') {
        // Top connector can only receive connections, not initiate them
        if (position === 'top') {
          return;
        }
      }
      
      // First click - start the connection
      this.isConnecting = true;
      this.startConnectionNodeId = nodeId;
      this.startConnectionPosition = position;
      
      // Get the connection point coordinates
      const point = event.target;
      const rect = point.getBoundingClientRect();
      const canvasRect = this.$refs.canvas.getBoundingClientRect();
      
      this.startConnectionPoint = {
        x: rect.left + rect.width / 2 - canvasRect.left,
        y: rect.top + rect.height / 2 - canvasRect.top
      };
      
      // Highlight the selected connection point
      point.style.backgroundColor = '#ffcc00';
      point.style.borderColor = '#ff9900';
      
      // Set initial temp connection path
      this.updateTempConnectionPath(this.mousePosition.x, this.mousePosition.y);
    },
    
    handleCanvasMouseMove(event) {
      const rect = this.$refs.canvas.getBoundingClientRect();
      this.mousePosition = {
        x: event.clientX - rect.left,
        y: event.clientY - rect.top
      };
      
      if (this.isConnecting) {
        this.updateTempConnectionPath(this.mousePosition.x, this.mousePosition.y);
      }
    },
    
    handleCanvasMouseUp(event) {
      // If we click on the canvas (not on a connection point), cancel the connection
      if (this.isConnecting && event.target === this.$refs.canvas) {
        // Reset connection state
        this.isConnecting = false;
        this.startConnectionNodeId = null;
        this.startConnectionPosition = null;
        this.tempConnectionPath = '';
        
        // Reset the highlight on any connection points
        const points = document.querySelectorAll('.connection-point');
        points.forEach(point => {
          point.style.backgroundColor = '#fff';
          point.style.borderColor = '#333';
        });
      }
    },
    
    updateTempConnectionPath(endX, endY) {
      const startX = this.startConnectionPoint.x;
      const startY = this.startConnectionPoint.y;
      const startPosition = this.startConnectionPosition;
      
      // Calculate control points for a curved path
      let controlPoint1X, controlPoint1Y, controlPoint2X, controlPoint2Y;
      
      // Adjust control points based on connection position
      if (startPosition === 'right') {
        controlPoint1X = startX + 50;
        controlPoint1Y = startY;
        controlPoint2X = endX - 50;
        controlPoint2Y = endY;
      } else if (startPosition === 'left') {
        controlPoint1X = startX - 50;
        controlPoint1Y = startY;
        controlPoint2X = endX + 50;
        controlPoint2Y = endY;
      } else if (startPosition === 'bottom') {
        controlPoint1X = startX;
        controlPoint1Y = startY + 50;
        controlPoint2X = endX;
        controlPoint2Y = endY - 50;
      } else if (startPosition === 'top') {
        controlPoint1X = startX;
        controlPoint1Y = startY - 50;
        controlPoint2X = endX;
        controlPoint2Y = endY + 50;
      } else if (startPosition === 'yes') {
        controlPoint1X = startX;
        controlPoint1Y = startY + 50;
        controlPoint2X = endX;
        controlPoint2Y = endY - 50;
      } else if (startPosition === 'no') {
        controlPoint1X = startX;
        controlPoint1Y = startY + 50;
        controlPoint2X = endX;
        controlPoint2Y = endY - 50;
      }
      
      // Calculate the midpoint of the path for placing the arrow
      const midX = (startX + endX) / 2;
      const midY = (startY + endY) / 2;
      
      // Create a curved path with a midpoint marker
      this.tempConnectionPath = `M${startX},${startY} Q${controlPoint1X},${controlPoint1Y} ${midX},${midY} Q${controlPoint2X},${controlPoint2Y} ${endX},${endY}`;
    },
    
    getConnectionPath(connection) {
      const startNodeId = connection.startNodeId;
      const startPosition = connection.startPosition;
      const endNodeId = connection.endNodeId;
      const endPosition = connection.endPosition;
      
      // Get connection points
      const startPoint = this.getConnectionPointCoordinates(
        document.querySelector(`.connection-point-${startPosition}[data-node-id="${startNodeId}"]`)
      );
      
      const endPoint = this.getConnectionPointCoordinates(
        document.querySelector(`.connection-point-${endPosition}[data-node-id="${endNodeId}"]`)
      );
      
      if (!startPoint || !endPoint) return '';
      
      // Calculate control points for a curved path
      let controlPoint1X, controlPoint1Y, controlPoint2X, controlPoint2Y;
      
      const dx = Math.abs(endPoint.x - startPoint.x);
      const dy = Math.abs(endPoint.y - startPoint.y);
      
      // Adjust control points based on connection positions
      if (startPosition === 'right' && endPosition === 'left') {
        // Horizontal connection
        controlPoint1X = startPoint.x + dx / 3;
        controlPoint1Y = startPoint.y;
        controlPoint2X = endPoint.x - dx / 3;
        controlPoint2Y = endPoint.y;
      } else if (startPosition === 'bottom' && endPosition === 'top') {
        // Vertical connection
        controlPoint1X = startPoint.x;
        controlPoint1Y = startPoint.y + dy / 3;
        controlPoint2X = endPoint.x;
        controlPoint2Y = endPoint.y - dy / 3;
      } else if (startPosition === 'yes' || startPosition === 'no') {
        // Yes/No connection from choice node
        controlPoint1X = startPoint.x;
        controlPoint1Y = startPoint.y + dy / 3;
        controlPoint2X = endPoint.x;
        controlPoint2Y = endPoint.y - dy / 3;
      } else if (endPosition === 'yes' || endPosition === 'no') {
        // Connection to Yes/No point of choice node
        controlPoint1X = startPoint.x;
        controlPoint1Y = startPoint.y + dy / 3;
        controlPoint2X = endPoint.x;
        controlPoint2Y = endPoint.y - dy / 3;
      } else {
        // Default curved connection
        controlPoint1X = startPoint.x + (endPoint.x - startPoint.x) / 2;
        controlPoint1Y = startPoint.y;
        controlPoint2X = startPoint.x + (endPoint.x - startPoint.x) / 2;
        controlPoint2Y = endPoint.y;
      }
      
      // Calculate the midpoint of the path for placing the arrow
      const midX = (startPoint.x + endPoint.x) / 2;
      const midY = (startPoint.y + endPoint.y) / 2;
      
      // Create a curved path with a midpoint marker
      return `M${startPoint.x},${startPoint.y} Q${controlPoint1X},${controlPoint1Y} ${midX},${midY} Q${controlPoint2X},${controlPoint2Y} ${endPoint.x},${endPoint.y}`;
    },
    
    getConnectionPointCoordinates(point) {
      if (!point) return null;
      
      const rect = point.getBoundingClientRect();
      const canvasRect = this.$refs.canvas.getBoundingClientRect();
      
      return {
        x: rect.left + rect.width / 2 - canvasRect.left,
        y: rect.top + rect.height / 2 - canvasRect.top
      };
    }
  }
};
</script>

<style scoped>
.canvas {
  width: 100%;
  height: 100%;
  position: relative;
}

.connections-layer {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
  z-index: 5;
}
</style>
