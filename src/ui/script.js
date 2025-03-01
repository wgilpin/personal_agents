document.addEventListener('DOMContentLoaded', () => {
    // Main application state
    const state = {
        nodes: [],
        connections: [],
        nextNodeId: 1,
        isDragging: false,
        isConnecting: false,
        selectedNode: null,
        startConnectionPoint: null,
        currentConnection: null,
        lastNodePosition: { x: 100, y: 100 } // Track the last node position
    };

    // DOM elements
    const canvas = document.getElementById('canvas');
    const nodeButtons = document.querySelectorAll('.node-button');
    const newFlowchartButton = document.getElementById('new-flowchart');
    const publishFlowchartButton = document.getElementById('publish-flowchart');

    // Initialize event listeners
    initEventListeners();

    // Function to initialize event listeners
    function initEventListeners() {
        // Node type buttons
        nodeButtons.forEach(button => {
            button.addEventListener('click', () => {
                const nodeType = button.getAttribute('data-type');
                
                // Position new node 20px right and 20px down from the last node
                const x = state.lastNodePosition.x + 20;
                const y = state.lastNodePosition.y + 20;
                
                // Ensure node is within canvas bounds (assuming canvas is at least 800x600)
                const boundedX = Math.max(20, Math.min(780, x));
                const boundedY = Math.max(20, Math.min(580, y));
                
                createNode(nodeType, boundedX, boundedY);
            });
        });

        // New flowchart button
        newFlowchartButton.addEventListener('click', createNewFlowchart);

        // Publish flowchart button
        publishFlowchartButton.addEventListener('click', publishFlowchart);

        // Canvas events for connection creation
        canvas.addEventListener('mousemove', handleCanvasMouseMove);
        canvas.addEventListener('mouseup', handleCanvasMouseUp);
    }

    // Function to create a new node
    function createNode(type, x = 100, y = 100, content = '', prompt = '') {
        const nodeId = `node-${state.nextNodeId++}`;
        const node = document.createElement('div');
        node.className = `node node-${type}`;
        node.id = nodeId;
        node.style.left = `${x}px`;
        node.style.top = `${y}px`;

        // Create node structure
        if (type === 'act') {
            node.innerHTML = `
                <div class="node-header">
                    <div class="node-title">${getNodeTitle(type)}</div>
                    <button class="node-delete">×</button>
                </div>
                <div class="node-content">
                    <div class="node-text" contenteditable="true">${content}</div>
                    <div class="prompt-container">
                        <label for="${nodeId}-prompt">Command:</label>
                        <textarea id="${nodeId}-prompt" class="node-prompt" placeholder="Enter command here...">${prompt}</textarea>
                    </div>
                </div>
            `;
        } else {
            node.innerHTML = `
                <div class="node-header">
                    <div class="node-title">${getNodeTitle(type)}</div>
                    <button class="node-delete">×</button>
                </div>
                <div class="node-content">
                    <div class="node-text" contenteditable="true">${content}</div>
                </div>
            `;
        }

        // Add connection points
        addConnectionPoints(node);

        // Add event listeners
        addNodeEventListeners(node);

        // Add to canvas
        canvas.appendChild(node);

        // Add to state
        state.nodes.push({
            id: nodeId,
            type,
            x,
            y,
            content,
            prompt: type === 'act' ? prompt : null
        });

        // Update last node position
        state.lastNodePosition = { x, y };

        return node;
    }

    // Function to get node title based on type
    function getNodeTitle(type) {
        switch (type) {
            case 'act': return 'Action';
            case 'choice': return 'Choice';
            case 'terminal': return 'Terminal';
            default: return 'Node';
        }
    }

    // Function to add connection points to a node
    function addConnectionPoints(node) {
        const positions = ['top', 'right', 'bottom', 'left'];
        
        positions.forEach(position => {
            const point = document.createElement('div');
            point.className = `connection-point connection-point-${position}`;
            point.setAttribute('data-position', position);
            point.setAttribute('data-node-id', node.id);
            
            // Add event listeners for connection points
            point.addEventListener('mousedown', handleConnectionStart);
            
            node.appendChild(point);
        });
    }

    // Function to add event listeners to a node
    function addNodeEventListeners(node) {
        // Drag functionality
        node.addEventListener('mousedown', handleNodeMouseDown);
        
        // Delete button
        const deleteButton = node.querySelector('.node-delete');
        deleteButton.addEventListener('click', () => deleteNode(node.id));
        
        // Editable content
        const contentElement = node.querySelector('.node-text');
        contentElement.addEventListener('mousedown', (e) => {
            e.stopPropagation();
        });
        
        contentElement.addEventListener('input', () => {
            updateNodeContent(node.id, contentElement.textContent);
        });
        
        // Prompt textarea (for action nodes only)
        const promptElement = node.querySelector('.node-prompt');
        if (promptElement) {
            // Prevent event propagation for the prompt textarea
            promptElement.addEventListener('mousedown', (e) => {
                e.stopPropagation();
            });
            
            promptElement.addEventListener('input', () => {
                updateNodePrompt(node.id, promptElement.value);
            });
        }
    }

    // Function to handle node mouse down (start dragging)
    function handleNodeMouseDown(e) {
        if (e.target.classList.contains('connection-point') || e.target.classList.contains('node-delete')) {
            return; // Don't start dragging if clicking on connection point or delete button
        }
        
        state.isDragging = true;
        state.selectedNode = this;
        
        // Calculate offset relative to the canvas
        const nodeRect = this.getBoundingClientRect();
        const canvasRect = canvas.getBoundingClientRect();
        
        // Get current node position from its style
        const currentLeft = parseInt(this.style.left) || 0;
        const currentTop = parseInt(this.style.top) || 0;
        
        // Calculate the offset between mouse position and node's current position
        state.dragOffsetX = e.clientX - (canvasRect.left + currentLeft);
        state.dragOffsetY = e.clientY - (canvasRect.top + currentTop);
        
        // Add event listeners for dragging
        document.addEventListener('mousemove', handleNodeDrag);
        document.addEventListener('mouseup', handleNodeDragEnd);
        
        // Prevent text selection during drag
        e.preventDefault();
    }

    // Function to handle node dragging
    function handleNodeDrag(e) {
        if (!state.isDragging || !state.selectedNode) return;
        
        const canvasRect = canvas.getBoundingClientRect();
        
        // Calculate new position relative to the canvas
        const x = e.clientX - canvasRect.left - state.dragOffsetX;
        const y = e.clientY - canvasRect.top - state.dragOffsetY;
        
        // Update node position
        state.selectedNode.style.left = `${x}px`;
        state.selectedNode.style.top = `${y}px`;
        
        // Update connections
        updateConnections(state.selectedNode.id, x, y);
    }

    // Function to handle node drag end
    function handleNodeDragEnd() {
        if (!state.isDragging || !state.selectedNode) return;
        
        // Update state
        const nodeIndex = state.nodes.findIndex(n => n.id === state.selectedNode.id);
        if (nodeIndex !== -1) {
            const x = parseInt(state.selectedNode.style.left);
            const y = parseInt(state.selectedNode.style.top);
            
            state.nodes[nodeIndex].x = x;
            state.nodes[nodeIndex].y = y;
            
            // Update last node position when a node is moved
            state.lastNodePosition = { x, y };
        }
        
        // Reset dragging state
        state.isDragging = false;
        state.selectedNode = null;
        
        // Remove event listeners
        document.removeEventListener('mousemove', handleNodeDrag);
        document.removeEventListener('mouseup', handleNodeDragEnd);
    }

    // Function to handle connection start
    function handleConnectionStart(e) {
        e.stopPropagation();
        
        // If we're already in connecting mode, this is the second click (end point)
        if (state.isConnecting && state.startConnectionPoint) {
            const endNodeId = this.getAttribute('data-node-id');
            const endPosition = this.getAttribute('data-position');
            
            // Don't connect to the same node
            if (endNodeId !== state.startConnectionPoint.getAttribute('data-node-id')) {
                createConnection(
                    state.startConnectionPoint.getAttribute('data-node-id'),
                    state.startConnectionPoint.getAttribute('data-position'),
                    endNodeId,
                    endPosition
                );
            }
            
            // Reset connection state
            state.isConnecting = false;
            state.startConnectionPoint = null;
            
            // Remove any temporary connection line
            if (state.currentConnection && state.currentConnection.element) {
                canvas.removeChild(state.currentConnection.element);
                state.currentConnection = null;
            }
            
            return;
        }
        
        // First click - start the connection
        state.isConnecting = true;
        state.startConnectionPoint = this;
        
        // Highlight the selected connection point
        this.style.backgroundColor = '#ffcc00';
        this.style.borderColor = '#ff9900';
        
        // Create temporary connection line with arrowhead (for visual feedback)
        const connectionId = `temp-connection`;
        const connection = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        connection.classList.add('connection-line');
        connection.id = connectionId;
        connection.style.position = 'absolute';
        connection.style.top = '0';
        connection.style.left = '0';
        connection.style.width = '100%';
        connection.style.height = '100%';
        connection.style.pointerEvents = 'none';
        
        // Add marker definition for arrowhead
        const markerId = `arrow-${connectionId}`;
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        defs.innerHTML = `
            <marker id="${markerId}" viewBox="0 0 10 10" refX="5" refY="5"
                markerWidth="6" markerHeight="6" orient="auto">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#333" />
            </marker>
        `;
        connection.appendChild(defs);
        
        // Add path with marker reference
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', 'M0,0 C0,0 0,0 0,0');
        path.setAttribute('marker-mid', `url(#${markerId})`);
        connection.appendChild(path);
        
        canvas.appendChild(connection);
        
        // Store the path reference and other connection data
        state.currentConnection = {
            id: connectionId,
            element: connection,
            path: path, // Use the direct path reference instead of querySelector
            startNodeId: this.getAttribute('data-node-id'),
            startPosition: this.getAttribute('data-position'),
            startPoint: getConnectionPointCoordinates(this)
        };
    }

    // Function to handle canvas mouse move (for connection creation)
    function handleCanvasMouseMove(e) {
        if (!state.isConnecting || !state.currentConnection) return;
        
        const rect = canvas.getBoundingClientRect();
        const endX = e.clientX - rect.left;
        const endY = e.clientY - rect.top;
        
        // Update connection path
        updateConnectionPath(
            state.currentConnection.path,
            state.currentConnection.startPoint.x,
            state.currentConnection.startPoint.y,
            endX,
            endY,
            state.currentConnection.startPosition
        );
    }

    // Function to handle canvas mouse up (for connection end)
    function handleCanvasMouseUp(e) {
        // We're now handling connections with clicks instead of drag
        // This function is kept for compatibility but doesn't do much
        
        // If we click on the canvas (not on a connection point), cancel the connection
        if (state.isConnecting && e.target === canvas) {
            // Reset connection state
            state.isConnecting = false;
            
            // Reset the highlight on the start connection point
            if (state.startConnectionPoint) {
                state.startConnectionPoint.style.backgroundColor = '#fff';
                state.startConnectionPoint.style.borderColor = '#333';
                state.startConnectionPoint = null;
            }
            
            // Remove temporary connection
            if (state.currentConnection && state.currentConnection.element) {
                canvas.removeChild(state.currentConnection.element);
                state.currentConnection = null;
            }
        }
    }

    // Function to create a permanent connection
    function createConnection(startNodeId, startPosition, endNodeId, endPosition) {
        const connectionId = `connection-${startNodeId}-${startPosition}-${endNodeId}-${endPosition}`;
        
        // Check if connection already exists
        if (state.connections.some(c => c.id === connectionId)) {
            return;
        }
        
        // Create SVG connection with arrowhead marker
        const connection = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        connection.classList.add('connection-line');
        connection.id = connectionId;
        connection.style.position = 'absolute';
        connection.style.top = '0';
        connection.style.left = '0';
        connection.style.width = '100%';
        connection.style.height = '100%';
        
        // Add marker definition for arrowhead
        const markerId = `arrow-${connectionId}`;
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        defs.innerHTML = `
            <marker id="${markerId}" viewBox="0 0 10 10" refX="5" refY="5"
                markerWidth="6" markerHeight="6" orient="auto">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#333" />
            </marker>
        `;
        connection.appendChild(defs);
        
        // Add path with marker reference
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', 'M0,0 C0,0 0,0 0,0');
        path.setAttribute('marker-mid', `url(#${markerId})`);
        connection.appendChild(path);
        
        canvas.appendChild(connection);
        
        // Get connection points
        const startPoint = getConnectionPointCoordinates(
            document.querySelector(`.connection-point-${startPosition}[data-node-id="${startNodeId}"]`)
        );
        
        const endPoint = getConnectionPointCoordinates(
            document.querySelector(`.connection-point-${endPosition}[data-node-id="${endNodeId}"]`)
        );
        
        // Update connection path
        updateConnectionPath(
            path,
            startPoint.x,
            startPoint.y,
            endPoint.x,
            endPoint.y,
            startPosition,
            endPosition
        );
        
        // Add to state
        state.connections.push({
            id: connectionId,
            element: connection,
            path: path,
            startNodeId,
            startPosition,
            endNodeId,
            endPosition
        });
    }

    // Function to update connections when a node moves
    function updateConnections(nodeId, x, y) {
        // Update connections where this node is the start
        state.connections.filter(c => c.startNodeId === nodeId).forEach(connection => {
            const startPoint = getConnectionPointCoordinates(
                document.querySelector(`.connection-point-${connection.startPosition}[data-node-id="${nodeId}"]`)
            );
            
            const endPoint = getConnectionPointCoordinates(
                document.querySelector(`.connection-point-${connection.endPosition}[data-node-id="${connection.endNodeId}"]`)
            );
            
            updateConnectionPath(
                connection.path,
                startPoint.x,
                startPoint.y,
                endPoint.x,
                endPoint.y,
                connection.startPosition,
                connection.endPosition
            );
        });
        
        // Update connections where this node is the end
        state.connections.filter(c => c.endNodeId === nodeId).forEach(connection => {
            const startPoint = getConnectionPointCoordinates(
                document.querySelector(`.connection-point-${connection.startPosition}[data-node-id="${connection.startNodeId}"]`)
            );
            
            const endPoint = getConnectionPointCoordinates(
                document.querySelector(`.connection-point-${connection.endPosition}[data-node-id="${nodeId}"]`)
            );
            
            updateConnectionPath(
                connection.path,
                startPoint.x,
                startPoint.y,
                endPoint.x,
                endPoint.y,
                connection.startPosition,
                connection.endPosition
            );
        });
    }

    // Function to get connection point coordinates
    function getConnectionPointCoordinates(point) {
        if (!point) return { x: 0, y: 0 };
        
        const rect = point.getBoundingClientRect();
        const canvasRect = canvas.getBoundingClientRect();
        
        return {
            x: rect.left + rect.width / 2 - canvasRect.left,
            y: rect.top + rect.height / 2 - canvasRect.top
        };
    }

    // Function to update connection path
    function updateConnectionPath(path, startX, startY, endX, endY, startPosition, endPosition) {
        if (!path) return;
        
        // Calculate control points for a curved path
        let controlPoint1X, controlPoint1Y, controlPoint2X, controlPoint2Y;
        
        const dx = Math.abs(endX - startX);
        const dy = Math.abs(endY - startY);
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        // Adjust control points based on connection positions
        if (startPosition === 'right' && endPosition === 'left') {
            // Horizontal connection
            controlPoint1X = startX + distance / 3;
            controlPoint1Y = startY;
            controlPoint2X = endX - distance / 3;
            controlPoint2Y = endY;
        } else if (startPosition === 'bottom' && endPosition === 'top') {
            // Vertical connection
            controlPoint1X = startX;
            controlPoint1Y = startY + distance / 3;
            controlPoint2X = endX;
            controlPoint2Y = endY - distance / 3;
        } else {
            // Default curved connection
            controlPoint1X = startX + (endX - startX) / 2;
            controlPoint1Y = startY;
            controlPoint2X = startX + (endX - startX) / 2;
            controlPoint2Y = endY;
        }
        
        // For temporary connections (during creation)
        if (!endPosition) {
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
            }
        }
        
        // Calculate the midpoint of the path for placing the arrow
        // For a curved path, we need to calculate a point along the curve
        const midX = (startX + endX) / 2;
        const midY = (startY + endY) / 2;
        
        // Create a curved path with a midpoint marker
        // We'll use a quadratic Bezier curve (Q) which naturally has a control point
        // This gives us a midpoint where the marker can be placed while keeping the curve
        const d = `M${startX},${startY} Q${controlPoint1X},${controlPoint1Y} ${midX},${midY} Q${controlPoint2X},${controlPoint2Y} ${endX},${endY}`;
        path.setAttribute('d', d);
    }

    // Function to delete a node
    function deleteNode(nodeId) {
        // Remove node element
        const node = document.getElementById(nodeId);
        if (node) {
            canvas.removeChild(node);
        }
        
        // Remove connections
        const connectionsToRemove = state.connections.filter(
            c => c.startNodeId === nodeId || c.endNodeId === nodeId
        );
        
        connectionsToRemove.forEach(connection => {
            if (connection.element) {
                canvas.removeChild(connection.element);
            }
        });
        
        // Update state
        state.nodes = state.nodes.filter(n => n.id !== nodeId);
        state.connections = state.connections.filter(
            c => c.startNodeId !== nodeId && c.endNodeId !== nodeId
        );
    }

    // Function to update node content
    function updateNodeContent(nodeId, content) {
        const nodeIndex = state.nodes.findIndex(n => n.id === nodeId);
        if (nodeIndex !== -1) {
            state.nodes[nodeIndex].content = content;
        }
    }
    
    // Function to update node prompt
    function updateNodePrompt(nodeId, prompt) {
        const nodeIndex = state.nodes.findIndex(n => n.id === nodeId);
        if (nodeIndex !== -1 && state.nodes[nodeIndex].type === 'act') {
            state.nodes[nodeIndex].prompt = prompt;
        }
    }

    // Function to create a new flowchart
    function createNewFlowchart() {
        // Clear canvas
        canvas.innerHTML = '';
        
        // Reset state
        state.nodes = [];
        state.connections = [];
        state.nextNodeId = 1;
        state.isDragging = false;
        state.isConnecting = false;
        state.selectedNode = null;
        state.startConnectionPoint = null;
        state.currentConnection = null;
        state.lastNodePosition = { x: 100, y: 100 }; // Reset last node position
    }

    // Function to publish the flowchart as YAML
    function publishFlowchart() {
        // Convert flowchart to YAML format
        const flowchartYaml = convertFlowchartToYaml();
        
        // Create a Blob with the YAML content
        const blob = new Blob([flowchartYaml], { type: 'text/yaml' });
        
        // Create a FormData object to send the file to the server
        const formData = new FormData();
        formData.append('file', blob, 'flowchart.yaml');
        
        // Show loading message
        const loadingMessage = document.createElement('div');
        loadingMessage.textContent = 'Publishing flowchart...';
        loadingMessage.style.position = 'fixed';
        loadingMessage.style.top = '50%';
        loadingMessage.style.left = '50%';
        loadingMessage.style.transform = 'translate(-50%, -50%)';
        loadingMessage.style.padding = '20px';
        loadingMessage.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
        loadingMessage.style.color = 'white';
        loadingMessage.style.borderRadius = '5px';
        loadingMessage.style.zIndex = '1000';
        document.body.appendChild(loadingMessage);
        
        // Send the file to the server
        fetch('http://localhost:8000/flowchart', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            // Remove loading message
            document.body.removeChild(loadingMessage);
            
            if (data.success) {
                // Show success message
                alert('Flowchart published successfully!');
                
                // Also save a local copy
                const downloadLink = document.createElement('a');
                downloadLink.href = URL.createObjectURL(blob);
                downloadLink.download = 'flowchart.yaml';
                downloadLink.click();
            } else {
                // Show error message
                alert(`Error publishing flowchart: ${data.message}`);
            }
        })
        .catch(error => {
            // Remove loading message
            document.body.removeChild(loadingMessage);
            
            // Show error message
            alert(`Error publishing flowchart: ${error.message}`);
            
            // Save a local copy anyway
            const downloadLink = document.createElement('a');
            downloadLink.href = URL.createObjectURL(blob);
            downloadLink.download = 'flowchart.yaml';
            downloadLink.click();
        });
    }
    
    // Function to convert flowchart to YAML format
    function convertFlowchartToYaml() {
        // Create a structured object for the flowchart
        const flowchart = {
            nodes: state.nodes.map(node => {
                // Create a clean node object without DOM references
                const cleanNode = {
                    id: node.id,
                    type: node.type,
                    position: {
                        x: node.x,
                        y: node.y
                    },
                    content: node.content
                };
                
                // Add prompt for action nodes
                if (node.type === 'act' && node.prompt) {
                    cleanNode.prompt = node.prompt;
                }
                
                return cleanNode;
            }),
            connections: state.connections.map(conn => {
                // Create a clean connection object without DOM references
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
        return convertToYaml(flowchart);
    }
    
    // Helper function to convert JavaScript object to YAML
    function convertToYaml(obj, indent = 0) {
        let yaml = '';
        const indentStr = ' '.repeat(indent);
        
        if (Array.isArray(obj)) {
            // Handle arrays
            for (const item of obj) {
                yaml += `${indentStr}- ${typeof item === 'object' ? '\n' + convertToYaml(item, indent + 2) : item}\n`;
            }
        } else if (typeof obj === 'object' && obj !== null) {
            // Handle objects
            for (const [key, value] of Object.entries(obj)) {
                if (typeof value === 'object' && value !== null) {
                    yaml += `${indentStr}${key}:\n${convertToYaml(value, indent + 2)}`;
                } else {
                    yaml += `${indentStr}${key}: ${value}\n`;
                }
            }
        }
        
        return yaml;
    }
});
